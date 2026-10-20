"""Portal telemetry. No sysfs writes, subprocesses, settings or root service.

CPUFreq frequencies are kHz; devfreq frequencies are Hz; thermal-zone and
hwmon temperatures are milli-Celsius; power-supply temperature is deci-Celsius.
Missing or malformed values stay None, distinct from a real zero reading.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from pathlib import Path
import re

MODEL = "AYN Odin 2 Portal"
SCHEMA_VERSION = 1


class Portal:
    def __init__(self, sys_root: Path = Path("/sys")):
        self.root = Path(sys_root)

    @staticmethod
    def text(path: Path) -> str | None:
        try:
            with path.open(encoding="utf-8") as stream:
                value = stream.read(4097)
            return value.rstrip("\0\r\n ") if len(value) <= 4096 else None
        except (OSError, UnicodeError):
            return None

    @classmethod
    def number(cls, path: Path, divisor: float = 1) -> float | None:
        try:
            value = float(cls.text(path)) / divisor
            return value if math.isfinite(value) else None
        except (TypeError, ValueError, OverflowError):
            return None

    @classmethod
    def steps(cls, path: Path, divisor: float) -> list[float]:
        values = []
        for part in (cls.text(path) or "").split():
            try:
                value = int(part) / divisor
                if value > 0:
                    values.append(value)
            except (ValueError, OverflowError):
                continue
        return sorted(set(values))

    def cpus(self) -> list[dict]:
        result = []
        paths = self.root.joinpath("devices/system/cpu/cpufreq").glob("policy*")
        for path in sorted(paths, key=lambda p: int(p.name[6:]) if p.name[6:].isdigit() else 9999):
            if not re.fullmatch(r"policy\d+", path.name):
                continue
            result.append({
                "id": path.name,
                "cpus": (self.text(path / "affected_cpus") or "").split(),
                "driver": self.text(path / "scaling_driver"),
                "governor": self.text(path / "scaling_governor"),
                "governors": (self.text(path / "scaling_available_governors") or "").split(),
                "current_mhz": self.number(path / "scaling_cur_freq", 1000),
                "minimum_mhz": self.number(path / "scaling_min_freq", 1000),
                "maximum_mhz": self.number(path / "scaling_max_freq", 1000),
                "hardware_maximum_mhz": self.number(path / "cpuinfo_max_freq", 1000),
                "available_mhz": self.steps(path / "scaling_available_frequencies", 1000),
            })
        return result

    def gpus(self) -> list[dict]:
        result = []
        for path in sorted(self.root.joinpath("class/devfreq").glob("*")):
            if not path.name.endswith(".gpu") or not (path / "governor").is_file():
                continue
            result.append({
                "id": path.name,
                "governor": self.text(path / "governor"),
                "governors": (self.text(path / "available_governors") or "").split(),
                "current_mhz": self.number(path / "cur_freq", 1_000_000),
                "minimum_mhz": self.number(path / "min_freq", 1_000_000),
                "maximum_mhz": self.number(path / "max_freq", 1_000_000),
                "available_mhz": self.steps(path / "available_frequencies", 1_000_000),
            })
        return result

    def fan(self) -> dict:
        matches = [p for p in sorted(self.root.joinpath("class/hwmon").glob("hwmon*"))
                   if self.text(p / "name") == "pwmfan"]
        if len(matches) != 1:
            return {"present": False, "reason": "ambiguous" if matches else "not-detected"}
        path = matches[0]
        pwm = self.number(path / "pwm1")
        if pwm is not None and not 0 <= pwm <= 255:
            pwm = None
        rpm = self.number(path / "fan1_input")
        return {"present": True, "driver": "pwmfan", "pwm": pwm,
                "duty_percent": round(pwm / 255 * 100, 1) if pwm is not None else None,
                "rpm": rpm if rpm is not None and rpm >= 0 else None,
                "enable_mode": self.number(path / "pwm1_enable")}

    def thermals(self) -> dict:
        sensors = []
        for path in sorted(self.root.joinpath("class/thermal").glob("thermal_zone*")):
            name = self.text(path / "type")
            value = self.number(path / "temp", 1000)
            if not name or value is None or not -40 <= value <= 180:
                continue
            group = "cpu" if re.match(r"cpu(?:ss|\d)", name) else (
                "gpu" if name.startswith(("gpuss", "gpu")) else (
                    "battery" if name == "battery" else "other"))
            sensors.append({"name": name, "group": group, "temperature_c": value})
        def hottest(group: str) -> float | None:
            return max((s["temperature_c"] for s in sensors if s["group"] == group), default=None)
        return {"cpu_c": hottest("cpu"), "gpu_c": hottest("gpu"),
                "battery_c": hottest("battery"), "sensors": sensors}

    def battery(self) -> dict:
        matches = [p for p in sorted(self.root.joinpath("class/power_supply").glob("*"))
                   if self.text(p / "type") == "Battery"]
        if len(matches) != 1:
            return {"present": False, "reason": "ambiguous" if matches else "not-detected"}
        path = matches[0]
        capacity = self.number(path / "capacity")
        return {"present": True, "status": self.text(path / "status"),
                "capacity_percent": capacity if capacity is not None and 0 <= capacity <= 100 else None,
                "power_w": self.number(path / "power_now", 1_000_000),
                "current_a": self.number(path / "current_now", 1_000_000),
                "voltage_v": self.number(path / "voltage_now", 1_000_000),
                "temperature_c": self.number(path / "temp", 10),
                "charge_limits_exposed": (path / "charge_control_end_threshold").exists(),
                "charge_limits_verified": False}

    def snapshot(self) -> dict:
        model = self.text(self.root / "firmware/devicetree/base/model")
        supported = model == MODEL
        result = {"schema_version": SCHEMA_VERSION,
                  "sampled_at": datetime.now(timezone.utc).isoformat(),
                  "supported": supported, "model": model,
                  "access": "read-only", "controls_available": False,
                  "cpus": [], "gpus": [], "fan": {"present": False},
                  "thermals": {"cpu_c": None, "gpu_c": None, "battery_c": None, "sensors": []},
                  "battery": {"present": False}}
        if not supported:
            result["reason"] = "This plugin currently supports the AYN Odin 2 Portal."
            return result
        result.update(cpus=self.cpus(), gpus=self.gpus(), fan=self.fan(),
                      thermals=self.thermals(), battery=self.battery())
        return result
