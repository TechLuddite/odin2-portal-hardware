import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from backend import lighting
from backend.controls import Engine
from test_controls import CheckedHardware, control_tree, TOKEN


class LightingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.path = self.root / "state/lights.json"
        self.hw = CheckedHardware(control_tree(self.root / "sys"))
        self.engine = Engine(self.hw, self.root / "journal/session.json", "boot-one", lambda: 0)
        self.engine.request(dict(op="fan", mode="auto", token=TOKEN))
        self.engine.request(dict(op="power", mode="saver", token=TOKEN))
        self.hw.writes.clear()

    def apply(self, **request):
        return lighting.apply(self.engine.request, dict(token=TOKEN, **request), self.path, "white")

    def rgb(self, side="both", brightness=128):
        return self.apply(op="rgb", side=side, red=180, green=0, blue=255, brightness=brightness)

    def test_manual_two_sides_readback_private_save_and_restart(self):
        result = self.rgb()
        self.assertFalse(result.get("error"), result)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.parent.stat().st_mode & 0o777, 0o700)
        saved = lighting.load(self.path)
        self.assertEqual(saved["sides"]["right"]["brightness"], 128)
        self.engine.restore()
        self.engine.request(dict(op="fan", mode="auto", token=TOKEN))
        result = self.apply(op="sync-lights")
        for side in lighting.SIDES:
            self.assertTrue(lighting.matches(result, side, saved["sides"][side]))

    def test_left_only_preserves_right_and_saves_independent_modes(self):
        self.rgb()
        before = self.engine.request(dict(op="status", token=TOKEN))
        result = self.apply(op="lighting", side="left", mode="theme", brightness=77)
        self.assertEqual(result["rings"]["r1"], before["rings"]["r1"])
        self.assertEqual(result["rings"]["l1"]["channels"], dict(red=255, green=255, blue=255))
        self.assertEqual([lighting.load(self.path)["sides"][s]["mode"] for s in lighting.SIDES], ["theme", "manual"])

    def test_off_preserves_theme_mode_across_new_theme_and_new_session(self):
        self.rgb()
        self.apply(op="lighting", side="both", mode="theme")
        self.apply(op="lights-off", side="both")
        self.assertEqual(lighting.load(self.path)["sides"]["left"]["brightness"], 128)
        self.assertFalse(lighting.load(self.path)["sides"]["left"]["enabled"])
        result = lighting.apply(self.engine.request, dict(op="sync-lights", token=TOKEN), self.path, "green")
        self.assertEqual(result["rings"]["l1"]["brightness"], 0)
        self.assertEqual(result["rings"]["l1"]["channels"], dict(red=0, green=255, blue=0))
        self.engine.restore()
        self.engine.request(dict(op="fan", mode="auto", token=TOKEN))
        self.assertEqual(self.apply(op="sync-lights")["rings"]["r4"]["brightness"], 0)
        self.assertEqual(lighting.load(self.path)["sides"]["left"]["mode"], "theme")

    def test_manual_ignores_theme_and_steady_sync_writes_nothing(self):
        self.rgb()
        self.hw.writes.clear()
        content = self.path.read_bytes()
        modified = self.path.stat().st_mtime_ns
        self.apply(op="sync-lights")
        self.assertEqual(self.hw.writes, [])
        self.assertEqual(self.path.read_bytes(), content)
        self.assertEqual(self.path.stat().st_mtime_ns, modified)

    def test_invalid_inputs_never_reach_helper(self):
        exchange = Mock()
        for request in [dict(op="rgb", side="both", red=-1, green=0, blue=0, brightness=128),
                        dict(op="rgb", side="both", red=255, green=0, blue=0, brightness=True),
                        dict(op="lighting", side="both", mode="bad"),
                        dict(op="lighting", side="both", mode="theme", extra=True),
                        dict(op="lights-off", side="all"), dict(op="sync-lights", token="bad")]:
            result = lighting.apply(exchange, {"token": TOKEN, **request}, self.path, "white")
            self.assertTrue(result.get("error"))
        exchange.assert_not_called()

    def test_unowned_session_and_failed_readback_do_not_save(self):
        result = lighting.apply(lambda _: {"owned": False, "occupied": True}, dict(op="sync-lights", token=TOKEN), self.path, "white")
        self.assertTrue(result.get("error"))
        current = self.engine.request(dict(op="status", token=TOKEN))
        fake = Mock(side_effect=[current, dict(current, error="readback failed")])
        result = lighting.apply(fake, dict(op="rgb", token=TOKEN, side="left", red=255, green=0, blue=0, brightness=77), self.path, "white")
        self.assertTrue(result.get("error"))
        self.assertEqual(fake.call_count, 2)
        self.assertFalse(self.path.exists())

    def test_missing_and_corrupt_preferences_do_not_change_leds(self):
        self.apply(op="sync-lights")
        self.assertEqual(self.hw.writes, [])
        self.path.write_text("broken")
        self.apply(op="sync-lights")
        self.assertEqual(self.path.read_text(), "broken")
        self.assertEqual(self.hw.writes, [])

    def test_guarded_adoption_records_actual_state_without_led_writes(self):
        self.rgb(brightness=166)
        current = self.engine.request(dict(op="status", token=TOKEN))
        self.path.unlink()
        self.hw.writes.clear()
        lighting.adopt(current, self.path)
        saved = lighting.load(self.path)
        self.assertEqual(saved["sides"]["left"]["brightness"], 166)
        self.assertEqual(saved["sides"]["left"]["mode"], "theme")
        self.assertEqual(self.hw.writes, [])
        self.assertTrue(lighting.describe(current, self.path, "white")["needs_sync"])

    def test_existing_manual_choice_survives_upgrade_adoption(self):
        self.rgb()
        original = self.path.read_bytes()
        lighting.adopt(self.engine.request(dict(op="status", token=TOKEN)), self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_off_restores_previous_brightness_on_explicit_apply(self):
        self.rgb(brightness=166)
        self.apply(op="lighting", side="both", mode="theme")
        self.apply(op="lights-off", side="both")
        self.assertEqual(lighting.load(self.path)["sides"]["left"]["brightness"], 166)
        result = self.apply(op="lighting", side="both", mode="theme", brightness=166)
        self.assertEqual(result["rings"]["l1"]["brightness"], 166)
        self.assertTrue(lighting.load(self.path)["sides"]["left"]["enabled"])

    def test_mixed_groups_are_not_flattened_on_adoption_or_mode_selection(self):
        self.engine.request(dict(op="rgb", side="left", red=255, green=0, blue=0, brightness=128, token=TOKEN))
        # Synthetic readback of externally mixed groups, no live device fixture.
        current = self.engine.request(dict(op="status", token=TOKEN))
        current["rings"]["l4"]["brightness"] = 64
        lighting.adopt(current, self.path)
        self.assertNotIn("left", lighting.load(self.path)["sides"])
        result = lighting.apply(lambda _: current, dict(op="lighting", side="left", mode="theme", token=TOKEN), self.path, "white")
        self.assertIn("groups differ", result["error"])

    def test_unavailable_theme_preserves_saved_color_and_explicit_follow_refuses(self):
        self.rgb()
        self.apply(op="lighting", side="both", mode="theme")
        current = lighting.apply(self.engine.request, dict(op="sync-lights", token=TOKEN), self.path, None)
        self.assertFalse(current.get("error"))
        result = lighting.apply(self.engine.request, dict(op="lighting", side="left", mode="theme", token=TOKEN), self.path, None)
        self.assertIn("unavailable", result["error"])

    def test_theme_replacement_light_neutral_keyboard_hint_and_hue_matching(self):
        current = self.root / "current/theme"
        stock = self.root / "stock"
        current.mkdir(parents=True)
        stock.mkdir()
        def theme(mode, accent):
            (current / "colors.toml").write_text(f'mode = "{mode}"\naccent = "{accent}"\n')
            return lighting.theme_color(current, stock)
        self.assertEqual(theme("light", "#205ea6"), "white")
        self.assertEqual(theme("dark", "#798186"), "white")  # Solitude
        self.assertEqual(theme("dark", "#509475"), "green")
        self.assertEqual(theme("dark", "#ff00ff"), "purple")
        self.assertEqual(theme("dark", "#7aa2f7"), "blue")
        tokyo = stock / "tokyo-night"
        tokyo.mkdir()
        (tokyo / "colors.toml").write_bytes((current / "colors.toml").read_bytes())
        (tokyo / "keyboard.rgb").write_text("ff00ff\n")
        self.assertEqual(lighting.theme_color(current, stock), "purple")
        (current / "colors.toml").write_text("accent = ")
        self.assertIsNone(lighting.theme_color(current, stock))
        current.rename(self.root / "old-theme")
        current.mkdir()
        self.assertEqual(theme("dark", "#82fb9c"), "green")


if __name__ == "__main__":
    unittest.main()
