"""Linux/DMS-native HTTP bridge for a Cync Bluetooth light mesh."""

import asyncio
import json
import math
import signal
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from aiohttp import web

from cync_ble import CyncBluetoothError, CyncBluetoothMesh
from state import (
    RuntimeState,
    load_meshes,
    load_state,
    next_morning,
    save_state,
    save_wake_deadline,
    validate_settings,
)


HOST = "127.0.0.1"
PORT = 8765
WARM_KELVIN = 2000
COOL_KELVIN = 6500
WAKE_ACK_FILE = Path("/run/cync-lights-wake.ack")
WAKE_ACK_TIMEOUT = 10


def kelvin_to_cync(kelvin):
    kelvin = min(max(kelvin, WARM_KELVIN), COOL_KELVIN)
    return round(1 + (kelvin - WARM_KELVIN) * 99 / (COOL_KELVIN - WARM_KELVIN))


def validate_kelvin(value):
    try:
        value = round(float(value))
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("kelvin must be a number") from error
    if not math.isfinite(value) or not 1000 <= value <= 10000:
        raise ValueError("kelvin must be between 1000 and 10000")
    return value


class RoomLights:
    def __init__(self, meshes, current=None):
        self.current = current or RuntimeState()
        self.targets = [
            (
                CyncBluetoothMesh(
                    [bulb["mac"] for bulb in mesh["bulbs"]], mesh["mac"], mesh["access_key"]
                ),
                mesh["bulbs"],
            )
            for mesh in meshes
        ]
        self.lock = asyncio.Lock()
        self.wake_task = None
        self.last_applied = None

    @property
    def online(self):
        return bool(self.targets) and all(transport.connected for transport, _bulbs in self.targets)

    def status(self):
        return self.current.public(self.online)

    async def sync(self, kelvin):
        kelvin = validate_kelvin(kelvin)
        desired = (kelvin, self.current.brightness, self.current.warmth)
        if desired == self.last_applied and self.online and self.current.lights_on:
            return
        self.current.kelvin = kelvin
        save_state(self.current)
        if not self.current.lights_on or self.current.wake_at:
            return
        adjusted = min(
            max(self.current.kelvin - self.current.warmth, WARM_KELVIN), COOL_KELVIN
        )
        temperature = kelvin_to_cync(adjusted)
        async with self.lock:
            for transport, bulbs in self.targets:
                await self._apply(transport, bulbs, temperature, self.current.brightness)
        self.last_applied = desired
        print(
            f"DMS: {self.current.kelvin}K -> {round(adjusted)}K, "
            f"{self.current.brightness}% brightness",
            flush=True,
        )

    async def update_settings(self, data):
        brightness, warmth, morning = validate_settings(data)
        changed = (brightness, warmth, morning) != (
            self.current.brightness,
            self.current.warmth,
            self.current.morning,
        )
        if not changed:
            return
        self.current.brightness = brightness
        self.current.warmth = warmth
        self.current.morning = morning
        if self.current.wake_at:
            self.current.wake_at = next_morning(morning)
            save_wake_deadline(self.current.wake_at)
            self._schedule_wake()
        save_state(self.current)
        if self.current.kelvin is not None and self.current.lights_on:
            await self.sync(self.current.kelvin)

    async def turn_off_until_morning(self):
        wake_at = next_morning(self.current.morning)
        previous_wake = self.current.wake_at
        self.current.wake_at = wake_at
        save_state(self.current)
        save_wake_deadline(wake_at)
        self._schedule_wake()
        try:
            await self._wait_for_wake_ack(wake_at)
        except CyncBluetoothError:
            self.current.wake_at = previous_wake
            save_state(self.current)
            save_wake_deadline(previous_wake)
            if previous_wake:
                self._schedule_wake()
            else:
                self._cancel_wake_task()
            print(
                "System wake timer was not verified; leaving the lights on.",
                flush=True,
            )
            raise

        print(f"System wake timer armed for {wake_at.isoformat()}.", flush=True)
        try:
            await self._set_power(False)
        except CyncBluetoothError:
            # A mesh write can fail after reaching only some bulbs. Keep the
            # wake deadline and the desired off state so every bulb is still
            # forced on in the morning.
            self.current.lights_on = False
            save_state(self.current)
            print(
                "Bluetooth shutdown was incomplete; the morning wake remains armed.",
                flush=True,
            )
            raise
        self.current.lights_on = False
        save_state(self.current)
        print("Lights are off; the morning wake remains armed.", flush=True)

    async def wake(self, only_if_due=False):
        if only_if_due and (
            not self.current.wake_at or self.current.wake_at > datetime.now().astimezone()
        ):
            return
        await self._set_power(True)
        self.current.lights_on = True
        self.current.wake_at = None
        self.last_applied = None
        save_state(self.current)
        save_wake_deadline(None)
        self._cancel_wake_task()
        if self.current.kelvin is not None:
            await self.sync(self.current.kelvin)

    async def restore(self):
        if self.current.wake_at:
            if self.current.wake_at <= datetime.now().astimezone():
                await self.wake()
            else:
                self.current.lights_on = False
                self._schedule_wake()
        elif self.current.lights_on and self.current.kelvin is not None:
            await self.sync(self.current.kelvin)

    async def _set_power(self, is_on):
        async with self.lock:
            for transport, bulbs in self.targets:
                await self._apply(transport, bulbs, power=is_on)

    async def _wait_for_wake_ack(self, wake_at):
        expected = wake_at.isoformat()
        deadline = asyncio.get_running_loop().time() + WAKE_ACK_TIMEOUT
        while asyncio.get_running_loop().time() < deadline:
            try:
                if WAKE_ACK_FILE.read_text(encoding="utf-8").strip() == expected:
                    return
            except OSError:
                pass
            await asyncio.sleep(0.1)
        raise CyncBluetoothError(
            "system wake timer could not be verified; lights were left on"
        )

    async def _apply(self, transport, bulbs, temperature=None, brightness=None, power=None):
        last_error = None
        for _attempt in range(2):
            try:
                if not transport.connected:
                    address = await transport.connect()
                    print(f"Connected to Cync mesh through {address}.", flush=True)
                for bulb in bulbs:
                    if power is None:
                        await transport.set_temperature(bulb["id"], temperature)
                        await asyncio.sleep(0.05)
                        await transport.set_brightness(bulb["id"], brightness)
                    else:
                        await transport.set_power(bulb["id"], power)
                return
            except Exception as error:
                last_error = error
                await transport.disconnect()
        raise CyncBluetoothError(str(last_error) or "Cync Bluetooth operation failed")

    def _schedule_wake(self):
        self._cancel_wake_task()
        self.wake_task = asyncio.create_task(self._wake_loop())

    def _cancel_wake_task(self):
        if self.wake_task and self.wake_task is not asyncio.current_task():
            self.wake_task.cancel()
        self.wake_task = None

    async def _wake_loop(self):
        while self.current.wake_at:
            delay = (self.current.wake_at - datetime.now().astimezone()).total_seconds()
            if delay > 0:
                await asyncio.sleep(min(delay, 30))
                continue
            try:
                await self.wake()
            except Exception as error:
                print(f"Morning wake retry: {error}", flush=True)
                await asyncio.sleep(60)

    async def close(self):
        self._cancel_wake_task()
        for transport, _bulbs in self.targets:
            with suppress(Exception):
                await transport.disconnect()


@web.middleware
async def errors(request, handler):
    try:
        return await handler(request)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise web.HTTPBadRequest(text=str(error)) from error
    except CyncBluetoothError as error:
        print(
            f"Request {request.method} {request.path} failed: {error}",
            flush=True,
        )
        raise web.HTTPServiceUnavailable(text=str(error)) from error


def create_app(lights):
    async def status(_request):
        return web.json_response(lights.status())

    async def sync(request):
        await lights.sync((await request.json())["kelvin"])
        return web.json_response(lights.status())

    async def settings(request):
        await lights.update_settings(await request.json())
        return web.json_response(lights.status())

    async def power(request):
        action = (await request.json())["action"]
        if action == "off_until_morning":
            await lights.turn_off_until_morning()
        elif action == "on":
            await lights.wake()
        elif action == "wake_if_due":
            await lights.wake(only_if_due=True)
        else:
            raise ValueError("unknown power action")
        return web.json_response(lights.status())

    app = web.Application(middlewares=[errors])
    app.router.add_get("/api/status", status)
    app.router.add_post("/api/sync", sync)
    app.router.add_post("/api/settings", settings)
    app.router.add_post("/api/power", power)
    return app


async def run():
    meshes = load_meshes()
    if meshes is None:
        raise SystemExit("No mesh credentials. Run ./setup-linux first.")

    current = load_state()
    save_state(current)
    save_wake_deadline(current.wake_at)
    lights = RoomLights(meshes, current)
    app = create_app(lights)
    runner = web.AppRunner(app, access_log=None)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop.set)

    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    print(f"DMS room-light bridge listening on http://{HOST}:{PORT}/api", flush=True)
    async def restore_desired_state():
        try:
            await lights.restore()
        except CyncBluetoothError as error:
            print(f"Initial Bluetooth sync failed: {error}", flush=True)

    restore_task = asyncio.create_task(restore_desired_state())

    async def reconnect_when_available():
        backoff = 30
        while True:
            await asyncio.sleep(backoff)
            if lights.current.lights_on and lights.current.kelvin is not None and not lights.online:
                try:
                    await lights.sync(lights.current.kelvin)
                    backoff = 30
                except CyncBluetoothError as error:
                    print(f"Bluetooth reconnect retry: {error}", flush=True)
                    backoff = min(backoff * 2, 300)
            else:
                backoff = 30

    reconnect_task = asyncio.create_task(reconnect_when_available())
    try:
        await stop.wait()
    finally:
        for task in (restore_task, reconnect_task):
            task.cancel()
            with suppress(asyncio.CancelledError, CyncBluetoothError):
                await task
        await runner.cleanup()
        with suppress(Exception):
            await lights.close()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except CyncBluetoothError as error:
        raise SystemExit(f"Cync error: {error}") from error
