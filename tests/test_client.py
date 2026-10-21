import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from backend.client import exchange
from backend.controls import Engine
from test_controls import CheckedHardware, TOKEN, control_tree


class QueuedColorHardware(CheckedHardware):
    """Model the observed stale nonzero brightness after a color update."""
    lag = False

    def __init__(self, root):
        super().__init__(root)
        self.pending = set()

    def write(self, key, value):
        group, field = key.split(".")
        if group in self.indices and self.lag:
            if field == "color" and int(self.read(group + ".brightness")):
                self.pending.add(group)
            elif field == "brightness":
                if int(value) == 0:
                    self.pending.discard(group)
                elif group in self.pending:
                    raise ValueError("Queued color update retained the previous brightness")
        super().write(key, value)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.request = dict(op="rgb", token=TOKEN, side="left", red=0, green=255, blue=0, brightness=64)

    def success(self, request):
        self.calls.append(dict(request))
        return dict(available=True, owned=True, rings={
            f"{side}{i}": {"brightness": request.get("brightness", 0)}
            for side in "lr" for i in range(1, 5)})

    def test_nonzero_rgb_is_off_then_target_without_mutating_request(self):
        original = dict(self.request)
        with patch("backend.client._exchange", side_effect=self.success):
            result = exchange(self.request)
        self.assertEqual([r["brightness"] for r in self.calls], [0, 64])
        self.assertEqual(self.request, original)
        self.assertEqual(result["rings"]["l1"]["brightness"], 64)
        self.assertTrue(all(r["side"] == "left" for r in self.calls))

    def test_off_is_one_operation(self):
        with patch("backend.client._exchange", side_effect=self.success):
            exchange(dict(self.request, brightness=0))
        self.assertEqual(len(self.calls), 1)

    def test_invalid_target_never_gets_a_preliminary_off(self):
        invalid = [dict(self.request, brightness=-1), dict(self.request, brightness=True),
                   dict(self.request, red=256), dict(self.request, side=[]),
                   dict(self.request, token="bad"), dict(self.request, extra="field")]
        for request in invalid:
            with self.subTest(request=request), patch("backend.client._exchange", return_value={"error": "refused"}) as raw:
                self.assertEqual(exchange(request), {"error": "refused"})
                raw.assert_called_once_with(request)

    def test_off_failure_or_missing_ownership_stops_before_target(self):
        for result in [dict(available=False, error="unavailable"), dict(available=True, owned=False),
                       dict(available=True, owned=True, error="refused")]:
            with self.subTest(result=result), patch("backend.client._exchange", return_value=result) as raw:
                self.assertTrue(exchange(self.request)["error"])
                self.assertEqual(raw.call_count, 1)

    def test_all_selected_groups_must_be_off(self):
        off = self.success(dict(self.request, brightness=0))
        off["rings"]["r4"]["brightness"] = 107
        with patch("backend.client._exchange", return_value=off) as raw:
            self.assertTrue(exchange(dict(self.request, side="both"))["error"])
            self.assertEqual(raw.call_count, 1)

    def test_target_error_is_returned_without_automatic_retry(self):
        off = self.success(dict(self.request, brightness=0))
        failure = dict(available=True, error="target failed")
        with patch("backend.client._exchange", side_effect=[off, failure]) as raw:
            self.assertEqual(exchange(self.request), failure)
            self.assertEqual(raw.call_count, 2)

    def test_non_rgb_requests_are_unchanged(self):
        for request in [dict(op="status", token=TOKEN), dict(op="fan", token=TOKEN, mode="max"),
                        dict(op="power", token=TOKEN, mode="performance"), dict(op="restore", token=TOKEN)]:
            with patch("backend.client._exchange", return_value={"ok": True}) as raw:
                self.assertEqual(exchange(request), {"ok": True})
                raw.assert_called_once_with(request)

    def test_raw_transaction_reproduces_modeled_color_race(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            hw = QueuedColorHardware(control_tree(root / "sys"))
            engine = Engine(hw, root / "session.json", "test-boot", lambda: 0)
            engine.request(dict(self.request, brightness=107))
            hw.lag = True
            with self.assertRaisesRegex(ValueError, "previous brightness"):
                engine.request(self.request)

    def test_workaround_survives_queued_color_race_and_preserves_other_groups(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            hw = QueuedColorHardware(control_tree(root / "sys"))
            engine = Engine(hw, root / "session.json", "test-boot", lambda: 0)
            engine.request(dict(op="fan", token=TOKEN, mode="max"))
            engine.request(dict(op="power", token=TOKEN, mode="performance"))
            engine.request(dict(self.request, side="both", brightness=107))
            before = {k: hw.read(k) for k in hw.paths}
            hw.lag = True
            with patch("backend.client._exchange", side_effect=engine.request):
                result = exchange(self.request)
            self.assertEqual(result["power_mode"], "performance")
            self.assertEqual(result["fan_mode"], "max")
            self.assertTrue(result["owned"])
            self.assertEqual(result["rings"]["l1"]["brightness"], 64)
            for key, value in before.items():
                if not key.startswith("l"):
                    self.assertEqual(hw.read(key), value, key)
            state = json.loads((root / "session.json").read_text())
            self.assertIn("0", state["groups"]["left"]["l1.brightness"]["allowed"])


if __name__ == "__main__":
    unittest.main()
