"""Fetch and store Cync Bluetooth mesh credentials."""

import asyncio
import getpass
import os

import aiohttp
from pycync import Auth
from pycync.const import REST_API_BASE_URL
from pycync.exceptions import CyncError, TwoFactorRequiredError

from cync_ble import CyncBluetoothError, normalize_mac
from state import MESH_FILE, save_meshes


async def login(session):
    username = os.getenv("CYNC_USERNAME") or input("Cync email: ").strip()
    password = os.getenv("CYNC_PASSWORD") or getpass.getpass("Cync password: ").strip()
    auth = Auth(session, username=username, password=password)
    try:
        await auth.login()
    except TwoFactorRequiredError:
        await auth.login(two_factor_code=input("2FA code: ").strip())
    return auth


async def fetch_meshes(auth):
    homes = await auth._send_user_request(
        f"{REST_API_BASE_URL}/v2/user/{auth.user.user_id}/subscribe/devices"
    )
    meshes = []
    for home in homes:
        if str(home.get("source")) != "5":
            continue
        properties = await auth._send_user_request(
            f"{REST_API_BASE_URL}/v2/product/{home['product_id']}/device/{home['id']}/property"
        )
        bulbs = [
            {"id": int(bulb["deviceID"]) % 1000, "mac": normalize_mac(bulb["mac"])}
            for bulb in properties.get("bulbsArray", [])
            if bulb.get("mac") and bulb.get("deviceID") is not None
        ]
        if not bulbs:
            continue
        if not home.get("mac") or home.get("access_key") is None:
            raise CyncBluetoothError("Cync did not return Bluetooth mesh credentials")
        meshes.append({"mac": home["mac"], "access_key": home["access_key"], "bulbs": bulbs})
    if not meshes:
        raise CyncBluetoothError("No Cync Bluetooth mesh was found")
    return meshes


async def run():
    async with aiohttp.ClientSession() as session:
        save_meshes(await fetch_meshes(await login(session)))
    print(f"Saved Cync mesh credentials to {MESH_FILE}.")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except (CyncError, CyncBluetoothError) as error:
        raise SystemExit(f"Cync error: {error}") from error
