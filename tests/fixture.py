"""Synthetic sysfs only: never opens a real hardware device."""
from pathlib import Path


def tree(root: Path) -> Path:
    files = {
        "firmware/devicetree/base/model": "AYN Odin 2 Portal\0",
        "devices/system/cpu/cpufreq/policy7/affected_cpus": "7",
        "devices/system/cpu/cpufreq/policy7/scaling_driver": "qcom-cpufreq-hw",
        "devices/system/cpu/cpufreq/policy7/scaling_governor": "schedutil",
        "devices/system/cpu/cpufreq/policy7/scaling_available_governors": "schedutil performance",
        "devices/system/cpu/cpufreq/policy7/scaling_cur_freq": "2092800",
        "devices/system/cpu/cpufreq/policy7/scaling_min_freq": "595200",
        "devices/system/cpu/cpufreq/policy7/scaling_max_freq": "2956800",
        "devices/system/cpu/cpufreq/policy7/cpuinfo_max_freq": "2956800",
        "devices/system/cpu/cpufreq/policy7/scaling_available_frequencies": "2956800 595200 2092800",
        "class/devfreq/3d00000.gpu/governor": "simple_ondemand",
        "class/devfreq/3d00000.gpu/available_governors": "simple_ondemand performance",
        "class/devfreq/3d00000.gpu/cur_freq": "680000000",
        "class/devfreq/3d00000.gpu/min_freq": "220000000",
        "class/devfreq/3d00000.gpu/max_freq": "680000000",
        "class/devfreq/3d00000.gpu/available_frequencies": "680000000 220000000",
        "class/hwmon/hwmon99/name": "pwmfan",
        "class/hwmon/hwmon99/pwm1": "70",
        "class/hwmon/hwmon99/pwm1_enable": "1",
        "class/hwmon/hwmon99/fan1_input": "2400",
        "class/thermal/thermal_zone7/type": "cpu7-middle-thermal",
        "class/thermal/thermal_zone7/temp": "95500",
        "class/thermal/thermal_zone8/type": "cpuss0-thermal",
        "class/thermal/thermal_zone8/temp": "40000",
        "class/thermal/thermal_zone9/type": "gpuss-0-thermal",
        "class/thermal/thermal_zone9/temp": "61000",
        "class/power_supply/battery/type": "Battery",
        "class/power_supply/battery/status": "Discharging",
        "class/power_supply/battery/capacity": "72",
        "class/power_supply/battery/power_now": "8250000",
        "class/power_supply/battery/current_now": "-2200000",
        "class/power_supply/battery/voltage_now": "3750000",
        "class/power_supply/battery/temp": "360",
        "class/power_supply/battery/charge_control_end_threshold": "0",
    }
    for name, value in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
    return root
