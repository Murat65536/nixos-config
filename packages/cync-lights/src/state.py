"""Persistent state for the Linux Cync room-light bridge."""

import json
import os
import stat
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path


DATA_DIR = Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local/state")) / "cync-lights"
MESH_FILE = DATA_DIR / "mesh.json"
STATE_FILE = DATA_DIR / "state.json"
WAKE_FILE = DATA_DIR / "wake.json"


@dataclass
class RuntimeState:
    brightness: int = 79
    warmth: int = 1500
    morning: str = "07:00"
    kelvin: int | None = None
    lights_on: bool = True
    wake_at: datetime | None = None

    def public(self, online=False):
        return {
            "online": online,
            "lights_on": self.lights_on,
            "wake_at": self.wake_at.isoformat() if self.wake_at else None,
            "kelvin": self.kelvin,
            "brightness": self.brightness,
        }


def validate_settings(data):
    try:
        brightness = round(float(data["brightness"]))
        warmth = round(float(data["warmth"]))
        morning = datetime.strptime(data.get("morning", "07:00"), "%H:%M").strftime("%H:%M")
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ValueError("brightness, warmth, or morning time is invalid") from error
    if not 0 <= brightness <= 100 or not -2000 <= warmth <= 2000:
        raise ValueError("brightness must be 0-100 and warmth must be -2000 to 2000")
    return brightness, warmth, morning


def next_morning(morning, now=None):
    now = now or datetime.now().astimezone()
    hour, minute = map(int, morning.split(":"))
    wake_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return wake_at + timedelta(days=1) if wake_at <= now else wake_at


def _parse_datetime(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed.astimezone() if parsed.tzinfo is None else parsed


def load_state():
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        brightness, warmth, morning = validate_settings(data)
        kelvin = data.get("kelvin")
        kelvin = round(float(kelvin)) if kelvin is not None else None
        wake_at = _parse_datetime(data.get("wake_at"))
        lights_on = bool(data.get("lights_on", not wake_at))
        return RuntimeState(brightness, warmth, morning, kelvin, lights_on, wake_at)
    except (OSError, json.JSONDecodeError, TypeError, ValueError, OverflowError):
        return RuntimeState()


def save_state(current):
    payload = asdict(current)
    payload["wake_at"] = current.wake_at.isoformat() if current.wake_at else None
    _atomic_json(STATE_FILE, payload)


def save_wake_deadline(wake_at):
    payload = {"wake_at": wake_at.isoformat() if wake_at else None}
    _atomic_json(WAKE_FILE, payload)


def load_meshes():
    try:
        meshes = json.loads(MESH_FILE.read_text(encoding="utf-8"))
        if not isinstance(meshes, list) or not meshes:
            raise ValueError("empty mesh cache")
        for mesh in meshes:
            if not isinstance(mesh, dict) or not {"mac", "access_key", "bulbs"} <= mesh.keys():
                raise ValueError("invalid mesh cache")
            if not isinstance(mesh["bulbs"], list) or not mesh["bulbs"]:
                raise ValueError("invalid bulb cache")
            for bulb in mesh["bulbs"]:
                if not isinstance(bulb, dict) or not {"id", "mac"} <= bulb.keys():
                    raise ValueError("invalid bulb cache")
        return meshes
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def save_meshes(meshes):
    if not meshes:
        raise ValueError("empty mesh cache")
    _atomic_json(MESH_FILE, meshes)


def _atomic_json(path, payload):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.chmod(stat.S_IRWXU)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.chmod(stat.S_IRUSR | stat.S_IWUSR)
    temporary.replace(path)
