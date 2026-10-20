import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.controls import Engine, Hardware, Refused
from fixture import tree

TOKEN = "fixture_session_0123456789"


def control_tree(root):
    tree(root)
    def put(name, value):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(value))
    for policy, cpus, maximum in [(0, "0 1 2", 2016000), (3, "3 4 5 6", 2803200), (7, "7", 2956800)]:
        base = f"devices/system/cpu/cpufreq/policy{policy}/"
        for key, value in {"related_cpus": cpus, "scaling_driver": "qcom-cpufreq-hw", "scaling_governor": "performance",
                           "scaling_available_governors": "schedutil performance", "scaling_min_freq": 300000,
                           "scaling_max_freq": maximum, "scaling_available_frequencies": f"300000 1000000 1800000 {maximum}"}.items():
            put(base + key, value)
    put("class/devfreq/3d00000.gpu/available_frequencies", "220000000 401000000 550000000 680000000")
    put("class/thermal/thermal_zone7/temp", 50000)
    for side in "lr":
        for index in range(1, 5):
            base = f"class/leds/rgb:{side}{index}/"
            for key, value in {"multi_index": "blue green red", "max_brightness": 255, "brightness": 0,
                               "multi_intensity": "255 255 255", "trigger": "[none] timer"}.items():
                put(base + key, value)
    return root


class CheckedHardware(Hardware):
    def __init__(self, root):
        super().__init__(root)
        self.writes = []
        self.fail_key = None

    def write(self, key, value):
        if self.fail_key == key:
            self.fail_key = None
            raise OSError("injected write failure")
        if key.endswith(".min"):
            assert int(value) <= int(self.read(key.replace(".min", ".max"))), "min exceeds max"
        if key.endswith(".max") and not key.startswith("gpu."):
            assert int(value) >= int(self.read(key.replace(".max", ".min"))), "max below min"
        super().write(key, value)
        self.writes.append((key, str(value)))


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.hw = CheckedHardware(control_tree(self.root / "sys"))
        self.now = 0
        self.journal = self.root / "state/session.json"
        self.engine = Engine(self.hw, self.journal, "boot-one", lambda: self.now)
        self.before = {key: self.hw.read(key) for key in self.hw.paths}

    def tearDown(self):
        self.temp.cleanup()

    def call(self, op, **values):
        return self.engine.request({"op": op, "token": TOKEN, **values})

    def assert_restored(self):
        self.assertEqual(self.before, {key: self.hw.read(key) for key in self.hw.paths})

    def test_initialization_and_status_do_not_write_hardware(self):
        self.assertFalse(self.call("status")["owned"])
        self.engine.tick()
        self.assertEqual(self.hw.writes, [])
        self.assertFalse(self.journal.exists())

    def test_all_power_presets_use_advertised_steps_and_restore(self):
        for mode in ("saver", "balanced", "performance"):
            self.assertEqual(self.call("power", mode=mode)["power_mode"], mode)
            for domain, spec in self.hw.domains.items():
                self.assertIn(int(self.hw.read(domain + ".max")), spec["steps"])
                self.assertLessEqual(int(self.hw.read(domain + ".max")), max(spec["steps"]))
        self.call("restore")
        self.assert_restored()

    def test_power_restores_elevated_original_minimum_safely(self):
        self.hw.write("policy7.min", 1800000)
        self.before["policy7.min"] = "1800000"
        self.call("power", mode="saver")
        self.call("restore")
        self.assert_restored()

    def test_power_preserves_gpu_minimum_and_governor(self):
        minimum = self.hw.root / "class/devfreq/3d00000.gpu/min_freq"
        governor = minimum.parent / "governor"
        minimum.write_text("440000000")  # Effective QoS boost, not an OPP step.
        governor.write_text("performance")
        self.call("power", mode="saver")
        self.call("restore")
        self.assertEqual(minimum.read_text(), "440000000")
        self.assertEqual(governor.read_text(), "performance")
        self.assertTrue(all(key not in {"gpu.min", "gpu.governor"} for key, _ in self.hw.writes))

    def test_rgb_uses_reported_bgr_order_and_only_selected_ring(self):
        self.call("rgb", side="left", red=255, green=32, blue=16, brightness=100)
        self.assertEqual(self.hw.read("l1.color"), "16 32 255")
        self.assertEqual(self.hw.read("r1.brightness"), "0")
        self.assertEqual(self.call("status")["rings"]["l1"]["channels"]["red"], 255)
        self.call("restore")
        self.assert_restored()

    def test_rgb_alternate_channel_order(self):
        self.hw.indices["r1"] = ["red", "blue", "green"]
        self.call("rgb", side="right", red=1, green=2, blue=3, brightness=128)
        self.assertEqual(self.hw.read("r1.color"), "1 3 2")

    def test_rgb_both_and_off_and_exact_recovery(self):
        self.call("rgb", side="both", red=150, green=4, blue=88, brightness=90)
        self.call("rgb", side="both", red=0, green=0, blue=0, brightness=0)
        self.call("restore")
        self.assert_restored()

    def test_manual_fan_and_temperature_override(self):
        self.call("fan", mode="manual", percent=30)
        self.assertEqual(self.hw.read("fan.pwm"), "77")
        (self.hw.root / "class/thermal/thermal_zone7/temp").write_text("90000")
        self.engine.tick()
        self.assertEqual(self.hw.read("fan.pwm"), "255")

    def test_missing_gpu_sensor_forces_full_speed(self):
        (self.hw.root / "class/thermal/thermal_zone9/temp").unlink()
        self.call("fan", mode="manual", percent=30)
        self.assertEqual(self.hw.read("fan.pwm"), "255")

    def test_stalled_fan_forces_full_speed(self):
        self.call("fan", mode="manual", percent=30)
        self.hw.rpm_path.write_text("0")
        for _ in range(5):
            self.engine.tick()
        self.assertEqual(self.hw.read("fan.pwm"), "255")

    def test_auto_fan_follows_hottest_sensor(self):
        self.call("fan", mode="auto")
        self.assertGreater(int(self.hw.read("fan.pwm")), 77)  # GPU is 61°C.
        self.call("restore")
        self.assert_restored()

    def test_dead_panel_lease_restores_all_groups(self):
        self.call("power", mode="saver")
        self.call("fan", mode="max")
        self.call("rgb", side="both", red=0, green=0, blue=255, brightness=40)
        for t in range(1, 12):
            self.now = t
            self.engine.tick()
        self.assert_restored()
        self.assertFalse(self.engine.groups)

    def test_closed_popup_heartbeat_keeps_lease(self):
        self.call("power", mode="balanced")
        for t in range(1, 30):
            self.now = t
            self.call("status")
            self.engine.tick()
        self.assertTrue(self.call("status")["owned"])

    def test_suspend_gap_recovers_even_with_fresh_heartbeat(self):
        self.call("power", mode="saver")
        self.now = 8
        self.call("status")
        self.engine.tick()
        self.assert_restored()

    def test_hot_recovery_keeps_full_fan_until_cool(self):
        self.call("fan", mode="auto")
        sensor = self.hw.root / "class/thermal/thermal_zone7/temp"
        sensor.write_text("90000")
        self.call("restore")
        self.assertEqual(self.hw.read("fan.pwm"), "255")
        self.assertTrue(self.call("status")["recovering"])
        sensor.write_text("50000")
        self.engine.tick()
        self.assert_restored()

    def test_daemon_restart_recovers_same_boot(self):
        self.call("power", mode="saver")
        self.call("fan", mode="auto")
        Engine(self.hw, self.journal, "boot-one", lambda: self.now)
        self.assert_restored()

    def test_different_boot_never_replays_old_values(self):
        self.call("power", mode="saver")
        self.hw.writes.clear()
        engine = Engine(self.hw, self.journal, "new-boot", lambda: self.now)
        self.assertFalse(engine.groups)
        self.assertEqual(self.hw.writes, [])

    def test_partial_transaction_failure_rolls_back(self):
        self.hw.fail_key = "policy3.max"
        with self.assertRaises(OSError):
            self.call("power", mode="saver")
        self.assert_restored()

    def test_asynchronous_cpu_limit_waits_for_kernel_readback(self):
        with patch.object(self.hw, "read", side_effect=["2016000", "2016000", "1000000"]) as read:
            Hardware.write(self.hw, "policy0.max", 1000000)
            self.assertEqual(read.call_count, 3)

    def test_write_accepted_then_readback_failure_remains_recoverable(self):
        original = self.hw.write
        def failed(key, value):
            original(key, value)
            if key == "policy3.max":
                self.hw.write = original
                raise Refused("injected post-write readback failure")
        self.hw.write = failed
        with self.assertRaises(Refused):
            self.call("power", mode="saver")
        self.assert_restored()

    def test_external_power_change_is_preserved(self):
        self.call("power", mode="saver")
        self.hw.write("policy0.max", 2016000)
        with self.assertRaises(Refused):
            self.call("power", mode="balanced")
        self.call("restore")
        self.assertEqual(self.hw.read("policy0.max"), "2016000")
        self.assertIn("Preserved external changes", self.engine.error)

    def test_second_session_cannot_control_or_renew_lease(self):
        self.call("fan", mode="max")
        with self.assertRaises(Refused):
            self.engine.request({"op": "restore", "token": "other_session_0123456789"})
        self.assertTrue(self.engine.request({"op": "status", "token": "other_session_0123456789"})["occupied"])

    def test_invalid_inputs_and_path_injection_write_nothing(self):
        bad = [{"op": "shell", "command": "true"}, {"op": "power", "mode": "overclock"},
               {"op": "fan", "mode": "manual", "percent": 0}, {"op": "fan", "mode": "off"},
               {"op": "fan", "mode": "manual", "percent": True},
               {"op": "rgb", "side": "../../etc", "red": 0, "green": 0, "blue": 0, "brightness": 0},
               {"op": "power", "mode": "saver", "path": "/etc/passwd"}]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(Refused):
                self.engine.request({"token": TOKEN, **value})
        self.assertEqual(self.hw.writes, [])

    def test_active_led_trigger_refuses_ring_control(self):
        (self.hw.root / "class/leds/rgb:l1/trigger").write_text("none [timer]")
        with self.assertRaises(Refused):
            self.call("rgb", side="left", red=255, green=0, blue=0, brightness=50)
        self.assertFalse(self.engine.groups)

    def test_journal_contains_only_logical_keys_and_precedes_writes(self):
        original = self.hw.write
        def checked(key, value):
            state = json.loads(self.journal.read_text())
            self.assertTrue(any(str(value) in group.get(key, {}).get("allowed", []) for group in state["groups"].values()))
            original(key, value)
        self.hw.write = checked
        self.call("power", mode="saver")
        self.assertNotIn("/sys", self.journal.read_text())

    def test_steady_fan_loop_does_not_rewrite_flash_journal(self):
        self.call("fan", mode="auto")
        stamp = self.journal.stat().st_mtime_ns
        for _ in range(10):
            self.engine.tick()
        self.assertEqual(self.journal.stat().st_mtime_ns, stamp)

    def test_wrong_board_and_topology_refused(self):
        (self.hw.root / "devices/system/cpu/cpufreq/policy7/related_cpus").write_text("6 7")
        with self.assertRaises(Refused):
            Hardware(self.hw.root)
        (self.hw.root / "firmware/devicetree/base/model").write_text("AYN Odin 2")
        with self.assertRaises(Refused):
            Hardware(self.hw.root)


if __name__ == "__main__":
    unittest.main()
