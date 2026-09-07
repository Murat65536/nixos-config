"""Minimal Cync/Telink Bluetooth mesh transport for Linux.

Protocol work is adapted from juanboro/cync2mqtt (MIT), itself derived from
google/python-laurel and google/python-dimond (Apache-2.0).

Copyright 2018 Google LLC
Licensed under the Apache License, Version 2.0 (the "License"); you may not
use this file except in compliance with the License. You may obtain a copy at
https://www.apache.org/licenses/LICENSE-2.0
"""

import asyncio
import random

from bleak import BleakClient, BleakScanner
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


class CyncBluetoothError(Exception):
    pass


def normalize_mac(mac):
    compact = mac.replace(":", "").replace("-", "").upper()
    try:
        valid = len(compact) == 12 and len(bytes.fromhex(compact)) == 6
    except ValueError:
        valid = False
    if not valid:
        raise CyncBluetoothError(f"Invalid bulb Bluetooth address: {mac!r}")
    return ":".join(compact[index:index + 2] for index in range(0, 12, 2))


def _encrypt(key, data):
    cipher = AES.new(bytes(reversed(key)), AES.MODE_ECB)
    return list(reversed(cipher.encrypt(bytes(reversed(data)))))


def _key_encrypt(name, password, key):
    data = [
        ord(left) ^ ord(right)
        for left, right in zip(name.ljust(16, "\0"), password.ljust(16, "\0"))
    ]
    return _encrypt(key, data)


def _session_key(name, password, local_random, remote_random):
    key = [
        ord(left) ^ ord(right)
        for left, right in zip(name.ljust(16, "\0"), password.ljust(16, "\0"))
    ]
    return _encrypt(key, local_random[:8] + remote_random[:8])


def _encrypt_packet(session_key, address, packet):
    nonce = address[:4] + [1] + packet[:3] + [15, 0, 0, 0, 0, 0, 0, 0]
    authenticator = _encrypt(session_key, nonce)
    for index in range(15):
        authenticator[index] ^= packet[index + 5]
    mac = _encrypt(session_key, authenticator)
    packet[3:5] = mac[:2]

    iv = [0] + address[:4] + [1] + packet[:3] + [0] * 7
    stream = _encrypt(session_key, iv)
    for index in range(15):
        packet[index + 5] ^= stream[index]
    return bytes(packet)


class CyncBluetoothMesh:
    NOTIFICATION_CHAR = "00010203-0405-0607-0809-0a0b0c0d1911"
    CONTROL_CHAR = "00010203-0405-0607-0809-0a0b0c0d1912"
    PAIRING_CHAR = "00010203-0405-0607-0809-0a0b0c0d1914"

    def __init__(self, bulb_macs, mesh_name, access_key):
        self.bulb_macs = [normalize_mac(mac) for mac in bulb_macs]
        self.mesh_name = mesh_name
        self.password = str(access_key)
        self.packet_count = random.randrange(0xFFFF)
        self.client = None
        self.session_key = None
        self.mac_data = None

    async def discover(self, timeout=8):
        expected = {mac.replace(":", "") for mac in self.bulb_macs}
        devices = await BleakScanner.discover(timeout=timeout)
        return [device for device in devices if device.address.replace(":", "").upper() in expected]

    async def connect(self):
        if self.connected:
            return self.client.address
        last_error = None
        saw_bulb = False
        for attempt in range(2):
            devices = await self.discover()
            saw_bulb = saw_bulb or bool(devices)
            for device in devices:
                client = BleakClient(device, timeout=15, disconnected_callback=self._disconnected)
                try:
                    await client.connect()
                    await self._authenticate(client, device.address)
                    self.client = client
                    return device.address
                except Exception as error:
                    last_error = error
                    if client.is_connected:
                        await client.disconnect()
            if attempt < 1:
                await asyncio.sleep(1)

        if not saw_bulb:
            raise CyncBluetoothError(
                "No saved Cync bulb is advertising over Bluetooth; it may already be connected"
            )
        detail = f": {last_error}" if last_error else ""
        raise CyncBluetoothError("Cync bulbs were visible but connection failed" + detail)

    def _disconnected(self, client):
        if self.client is client:
            self.client = None
            self.session_key = None
            self.mac_data = None

    async def _authenticate(self, client, address):
        compact_mac = normalize_mac(address).replace(":", "")
        self.mac_data = list(reversed(bytes.fromhex(compact_mac)))

        local_random = list(get_random_bytes(8))
        data = local_random + [0] * 8
        login = bytes([0x0C] + local_random + _key_encrypt(self.mesh_name, self.password, data)[:8])
        await client.write_gatt_char(self.PAIRING_CHAR, login, response=True)
        await asyncio.sleep(0.3)
        response = list(await client.read_gatt_char(self.PAIRING_CHAR))
        if len(response) < 9:
            raise CyncBluetoothError("Bulb returned an invalid mesh authentication response")

        self.session_key = _session_key(self.mesh_name, self.password, local_random, response[1:9])
        await client.start_notify(self.NOTIFICATION_CHAR, lambda _sender, _data: None)
        await client.write_gatt_char(self.NOTIFICATION_CHAR, b"\x01", response=True)
        await asyncio.sleep(0.3)
        await client.read_gatt_char(self.NOTIFICATION_CHAR)

    async def send(self, target, command, data):
        if not self.client or not self.client.is_connected or not self.session_key:
            raise CyncBluetoothError("Bluetooth mesh is not connected")

        packet = [0] * 20
        packet[0] = self.packet_count & 0xFF
        packet[1] = (self.packet_count >> 8) & 0xFF
        packet[5] = target & 0xFF
        packet[6] = (target >> 8) & 0xFF
        packet[7:10] = [command, 0x11, 0x02]
        packet[10:10 + len(data)] = data
        encrypted = _encrypt_packet(self.session_key, self.mac_data, packet)
        self.packet_count = 1 if self.packet_count == 0xFFFF else self.packet_count + 1
        await self.client.write_gatt_char(self.CONTROL_CHAR, encrypted, response=False)

    async def set_temperature(self, target, temperature):
        await self.send(target, 0xE2, [0x05, temperature])

    async def set_brightness(self, target, brightness):
        await self.send(target, 0xD2, [brightness])

    async def set_power(self, target, is_on):
        await self.send(target, 0xD0, [int(is_on)])

    @property
    def connected(self):
        return bool(self.client and self.client.is_connected and self.session_key)

    async def disconnect(self):
        client = self.client
        self.client = None
        self.session_key = None
        self.mac_data = None
        if client and client.is_connected:
            await client.disconnect()
