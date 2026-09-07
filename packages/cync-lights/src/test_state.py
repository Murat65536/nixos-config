import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import state


class StateTest(unittest.TestCase):
    def test_settings_validation(self):
        self.assertEqual(state.validate_settings({"brightness": 72, "warmth": 800}), (72, 800, "07:00"))
        with self.assertRaises(ValueError):
            state.validate_settings({"brightness": 101, "warmth": 0})

    def test_next_morning_is_timezone_aware_and_one_shot(self):
        now = datetime.now().astimezone().replace(hour=21, minute=0, second=0, microsecond=0)
        result = state.next_morning("07:00", now)
        self.assertIsNotNone(result.tzinfo)
        self.assertEqual(result.date(), (now + state.timedelta(days=1)).date())
        self.assertEqual((result.hour, result.minute), (7, 0))

    def test_loads_saved_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            saved = root / "state.json"
            saved.write_text(
                json.dumps({
                    "brightness": 56,
                    "warmth": 1200,
                    "morning": "06:30",
                    "kelvin": 4100,
                    "lights_on": True,
                    "wake_at": None,
                }),
                encoding="utf-8",
            )
            with patch.object(state, "STATE_FILE", saved):
                loaded = state.load_state()
        self.assertEqual(loaded.kelvin, 4100)
        self.assertEqual(loaded.morning, "06:30")

    def test_atomic_state_and_wake_files_are_private(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_file = root / "state.json"
            wake_file = root / "wake.json"
            with patch.object(state, "DATA_DIR", root), patch.object(
                state, "STATE_FILE", state_file
            ), patch.object(state, "WAKE_FILE", wake_file):
                current = state.RuntimeState(kelvin=4000)
                state.save_state(current)
                state.save_wake_deadline(None)
            self.assertEqual(state_file.stat().st_mode & 0o777, 0o600)
            self.assertEqual(wake_file.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(wake_file.read_text())["wake_at"], None)


if __name__ == "__main__":
    unittest.main()
