import asyncio
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiohttp.test_utils import TestClient, TestServer

import bridge
from state import RuntimeState


class RoomLightsTest(unittest.IsolatedAsyncioTestCase):
    def make_lights(self, current=None):
        mesh = {
            "mac": "mesh",
            "access_key": 123,
            "bulbs": [
                {"id": 100, "mac": "11:22:33:44:55:66"},
                {"id": 201, "mac": "22:33:44:55:66:77"},
            ],
        }
        transport = SimpleNamespace(
            connected=True,
            connect=AsyncMock(return_value="11:22:33:44:55:66"),
            set_temperature=AsyncMock(),
            set_brightness=AsyncMock(),
            set_power=AsyncMock(),
            disconnect=AsyncMock(),
        )
        with patch.object(bridge, "CyncBluetoothMesh", return_value=transport):
            lights = bridge.RoomLights([mesh], current)
        return lights, transport

    async def test_sync_maps_dms_temperature_and_brightness(self):
        lights, transport = self.make_lights(RuntimeState(brightness=50, warmth=1000))
        with patch.object(bridge, "save_state"):
            await lights.sync(5000)

        self.assertEqual(
            [call.args for call in transport.set_temperature.await_args_list],
            [(100, 45), (201, 45)],
        )
        self.assertEqual(
            [call.args for call in transport.set_brightness.await_args_list],
            [(100, 50), (201, 50)],
        )

    async def test_sync_does_not_turn_scheduled_off_lights_back_on(self):
        current = RuntimeState(lights_on=False, wake_at=datetime.now().astimezone())
        lights, transport = self.make_lights(current)
        with patch.object(bridge, "save_state"):
            await lights.sync(3500)
        transport.set_temperature.assert_not_awaited()

    async def test_duplicate_dms_value_is_not_sent_twice(self):
        lights, transport = self.make_lights()
        with patch.object(bridge, "save_state"):
            await lights.sync(5000)
            await lights.sync(5000)
        self.assertEqual(transport.set_temperature.await_count, 2)

    async def test_failed_off_keeps_verified_wake_deadline(self):
        lights, transport = self.make_lights()
        transport.set_power.side_effect = RuntimeError("write failed")
        with patch.object(bridge, "save_state") as save, patch.object(
            bridge, "save_wake_deadline"
        ) as save_wake, patch.object(
            lights, "_wait_for_wake_ack", AsyncMock()
        ), patch.object(lights, "_schedule_wake"):
            with self.assertRaises(bridge.CyncBluetoothError):
                await lights.turn_off_until_morning()
        self.assertFalse(lights.current.lights_on)
        self.assertIsNotNone(lights.current.wake_at)
        self.assertEqual(save.call_count, 2)
        save_wake.assert_called_once_with(lights.current.wake_at)

    async def test_successful_off_persists_one_wake_deadline(self):
        lights, transport = self.make_lights()
        with patch.object(bridge, "save_state") as save, patch.object(
            bridge, "save_wake_deadline"
        ) as save_wake, patch.object(
            lights, "_wait_for_wake_ack", AsyncMock()
        ) as wait_for_ack, patch.object(lights, "_schedule_wake"):
            await lights.turn_off_until_morning()
        self.assertFalse(lights.current.lights_on)
        self.assertIsNotNone(lights.current.wake_at)
        self.assertEqual(transport.set_power.await_count, 2)
        self.assertEqual(save.call_count, 2)
        save_wake.assert_called_once_with(lights.current.wake_at)
        wait_for_ack.assert_awaited_once_with(lights.current.wake_at)

    async def test_unverified_wake_leaves_lights_on_and_clears_deadline(self):
        lights, transport = self.make_lights()
        no_ack = bridge.CyncBluetoothError("no timer acknowledgment")
        with patch.object(bridge, "save_state") as save, patch.object(
            bridge, "save_wake_deadline"
        ) as save_wake, patch.object(
            lights, "_wait_for_wake_ack", AsyncMock(side_effect=no_ack)
        ), patch.object(lights, "_schedule_wake"), patch.object(
            lights, "_cancel_wake_task"
        ):
            with self.assertRaises(bridge.CyncBluetoothError):
                await lights.turn_off_until_morning()
        self.assertTrue(lights.current.lights_on)
        self.assertIsNone(lights.current.wake_at)
        transport.set_power.assert_not_awaited()
        self.assertEqual(save.call_count, 2)
        self.assertEqual(save_wake.call_count, 2)
        self.assertIsNone(save_wake.call_args_list[-1].args[0])

    async def test_wake_if_due_is_a_noop_before_deadline(self):
        future = bridge.next_morning("07:00")
        lights, transport = self.make_lights(RuntimeState(lights_on=False, wake_at=future))
        await lights.wake(only_if_due=True)
        transport.set_power.assert_not_awaited()

    async def test_wake_loop_rechecks_wall_time_after_suspend(self):
        lights, _transport = self.make_lights()
        lights.current.wake_at = bridge.next_morning("07:00")
        with patch.object(asyncio, "sleep", AsyncMock(side_effect=asyncio.CancelledError)) as sleep:
            with self.assertRaises(asyncio.CancelledError):
                await lights._wake_loop()
        self.assertLessEqual(sleep.await_args.args[0], 30)


class ApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.lights = SimpleNamespace(
            status=lambda: {"online": True, "lights_on": True, "wake_at": None},
            sync=AsyncMock(),
            update_settings=AsyncMock(),
            turn_off_until_morning=AsyncMock(),
            wake=AsyncMock(),
        )
        self.client = TestClient(TestServer(bridge.create_app(self.lights)))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_status_and_sync_api(self):
        response = await self.client.get("/api/status")
        self.assertEqual(response.status, 200)
        self.assertTrue((await response.json())["online"])
        response = await self.client.post("/api/sync", json={"kelvin": 4200})
        self.assertEqual(response.status, 200)
        self.lights.sync.assert_awaited_once_with(4200)

    async def test_unknown_power_action_is_rejected(self):
        response = await self.client.post("/api/power", json={"action": "party"})
        self.assertEqual(response.status, 400)


if __name__ == "__main__":
    unittest.main()
