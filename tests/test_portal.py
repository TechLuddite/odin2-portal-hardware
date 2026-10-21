import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.portal import Portal
from fixture import tree


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = tree(Path(self.tmp.name))
        self.adapter = Portal(self.root)

    def set(self, path, value):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value)

    def test_exact_portal_identity_required_before_discovery(self):
        for model in ["AYN Odin 2", "AYN Odin 2 Mini", "AYN Thor", "SM8550", "AYN Odin 2 Portal clone"]:
            self.set("firmware/devicetree/base/model", model)
            with patch.object(self.adapter, "cpus", side_effect=AssertionError("must not probe")):
                self.assertFalse(self.adapter.snapshot()["supported"])

    def test_absent_model_is_unsupported(self):
        (self.root / "firmware/devicetree/base/model").unlink()
        self.assertFalse(self.adapter.snapshot()["supported"])

    def test_cpu_frequencies_are_khz(self):
        cpu = self.adapter.snapshot()["cpus"][0]
        self.assertEqual(cpu["current_mhz"], 2092.8)
        self.assertEqual(cpu["hardware_maximum_mhz"], 2956.8)
        self.assertEqual(cpu["available_mhz"], [595.2, 2092.8, 2956.8])
        self.assertEqual(cpu["cpus"], ["7"])

    def test_gpu_frequencies_are_hz(self):
        gpu = self.adapter.snapshot()["gpus"][0]
        self.assertEqual(gpu["current_mhz"], 680)
        self.assertEqual(gpu["available_mhz"], [220, 680])

    def test_storage_telemetry_uses_hz_without_claiming_preset_ownership(self):
        storage=self.adapter.snapshot()['storage'][0]
        self.assertEqual((storage['governor'],storage['current_mhz']),('performance',300))
        self.assertEqual(storage['available_mhz'],[75,150,300])
        self.assertTrue(all(p['storage']=='unchanged' for p in self.adapter.snapshot()['power_presets']))

    def test_preset_previews_match_reviewed_advertised_caps_and_do_not_pin_minimums(self):
        from test_controls import control_tree
        control_tree(self.root)
        plans=self.adapter.snapshot()['power_presets']
        self.assertEqual([p['mode'] for p in plans],['saver','balanced','performance'])
        self.assertEqual([[c['maximum_mhz'] for c in p['cpus']] for p in plans],
                         [[1000,1800,1800],[1000,1800,1800],[2016,2803.2,2956.8]])
        self.assertEqual([p['gpu_maximum_mhz'] for p in plans],[401,680,680])
        for plan in plans:
            self.assertTrue(all(c['minimum_mhz']==300 and not c['minimum_equals_maximum'] for c in plan['cpus']))
            self.assertEqual(plan['gpu_governor'],'unchanged')
            self.assertEqual(plan['gpu_minimum'],'unchanged')
        self.assertEqual(plans[-1]['cpus'][0]['behavior'],'requests-ceiling')
        self.assertEqual(plans[0]['cpus'][0]['behavior'],'stepped-scaling')

    def test_missing_steps_do_not_invent_zero_frequency_or_pin(self):
        self.set('devices/system/cpu/cpufreq/policy7/scaling_available_frequencies','')
        cpu=self.adapter.snapshot()['power_presets'][0]['cpus'][0]
        self.assertIsNone(cpu['minimum_mhz'])
        self.assertIsNone(cpu['maximum_mhz'])
        self.assertIsNone(cpu['minimum_equals_maximum'])

    def test_hottest_cpu_is_not_diluted_by_other_sensors(self):
        self.assertEqual(self.adapter.snapshot()["thermals"]["cpu_c"], 95.5)
        self.assertEqual(self.adapter.snapshot()["thermals"]["gpu_c"], 61)

    def test_invalid_temperature_is_excluded(self):
        self.set("class/thermal/thermal_zone7/temp", "999000")
        self.assertEqual(self.adapter.thermals()["cpu_c"], 40)

    def test_missing_sensor_does_not_become_zero(self):
        (self.root / "class/thermal/thermal_zone9/temp").unlink()
        self.assertIsNone(self.adapter.thermals()["gpu_c"])

    def test_fan_discovered_by_name_not_index(self):
        self.assertEqual(self.adapter.snapshot()["fan"]["rpm"], 2400)
        self.assertEqual(self.adapter.snapshot()["fan"]["duty_percent"], 27.5)

    def test_fan_cooling_level_never_substitutes_for_pwm(self):
        self.set("class/thermal/cooling_device1/type", "pwm-fan")
        self.set("class/thermal/cooling_device1/cur_state", "7")
        self.assertEqual(self.adapter.fan()["duty_percent"], 27.5)

    def test_ambiguous_fan_does_not_choose_first(self):
        self.set("class/hwmon/hwmon1/name", "pwmfan")
        self.assertEqual(self.adapter.fan(), {"present": False, "reason": "ambiguous"})

    def test_zero_fan_is_a_real_zero(self):
        self.set("class/hwmon/hwmon99/pwm1", "0")
        self.set("class/hwmon/hwmon99/fan1_input", "0")
        self.assertEqual(self.adapter.fan()["rpm"], 0)
        self.assertEqual(self.adapter.fan()["duty_percent"], 0)

    def test_invalid_pwm_is_unavailable(self):
        self.set("class/hwmon/hwmon99/pwm1", "256")
        self.assertIsNone(self.adapter.fan()["duty_percent"])

    def test_battery_units_and_current_sign(self):
        battery = self.adapter.battery()
        self.assertEqual(battery["power_w"], 8.25)
        self.assertEqual(battery["voltage_v"], 3.75)
        self.assertEqual(battery["current_a"], -2.2)
        self.assertEqual(battery["temperature_c"], 36)

    def test_exposed_charge_limit_is_not_claimed_verified(self):
        self.assertTrue(self.adapter.battery()["charge_limits_exposed"])
        self.assertFalse(self.adapter.battery()["charge_limits_verified"])

    def test_invalid_numbers_stay_unavailable_and_json_is_finite(self):
        for value in ["nan", "inf", "-inf", "garbage", ""]:
            self.set("class/power_supply/battery/power_now", value)
            snapshot = self.adapter.snapshot()
            self.assertIsNone(snapshot["battery"]["power_w"])
            json.dumps(snapshot, allow_nan=False)

    def test_oversized_attributes_are_not_read_unboundedly(self):
        self.set("class/hwmon/hwmon99/name", "pwmfan" + " " * 4096)
        self.assertFalse(self.adapter.fan()["present"])

    def test_snapshot_does_not_change_tree(self):
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = self.adapter.snapshot()
        after = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result["access"], "read-only")
        self.assertFalse(result["controls_available"])

    def test_real_cli_on_fixture(self):
        p = Path(__file__).resolve().parents[1] / "bin/odin2-portal-hardware"
        proc = subprocess.run([sys.executable, "-I", "-B", str(p), "--sys-root", str(self.root)],
                              text=True, capture_output=True, check=True, timeout=5)
        self.assertTrue(json.loads(proc.stdout)["supported"])
        self.assertEqual(proc.stderr, "")


if __name__ == "__main__":
    unittest.main()
