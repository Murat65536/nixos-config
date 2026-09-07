# DMS Cync room lights

This is a Linux-only Bluetooth bridge for the `cyncLights` Dank Material Shell plugin.

## Architecture

- `CyncLightsDaemon.qml` follows DMS night-light temperature continuously.
- `CyncLights.qml` provides the Control Center status and power toggle.
- `bridge.py` exposes a localhost-only JSON API and owns desired light state.
- `cync_ble.py` speaks the Cync/Telink Bluetooth mesh protocol through BlueZ/Bleak.
- `state.py` atomically stores private runtime state and a separate RTC wake deadline.
- Home Manager owns the user bridge; NixOS owns the privileged `WakeSystem`
  timer scheduler and suspend coordination.
- `setup.py` is the only component that talks to the Cync cloud; normal operation is local.

## Setup

After deploying the NixOS configuration, run:

```console
cync-lights-setup
```

Mesh credentials are stored with mode `0600` in
`~/.local/state/cync-lights/mesh.json`.

## Verification

```console
nix build .#checks.x86_64-linux.cync-lights
curl -fsS http://127.0.0.1:8765/api/status
systemctl --user status cync-lights.service
```

The bridge starts its API before attempting Bluetooth and retries disconnected bulbs without
crashing. A graceful systemd stop disconnects the active mesh gateway so BlueZ does not retain a
stale connection.
