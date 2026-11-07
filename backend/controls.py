"""Narrow Portal control engine. Only the separately installed root daemon uses it.

No command execution, user paths, kernel tuning, fan-off or overclocking API.
Session leases restore the captured state after the UI stops heartbeating.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import time

from .portal import MODEL, Portal


class Refused(ValueError):
    pass


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise Refused(f"Expected an integer from {low} to {high}")
    return value


def plan_power(domains, mode):
    if mode not in {"saver", "balanced", "performance"}:
        raise Refused("Unknown Linux power preset")
    changes = []
    for domain, spec in domains.items():
        steps = spec["steps"]
        fraction = 0.65 if mode == "saver" else (0.85 if mode == "balanced" and domain != "gpu" else 1)
        maximum = max(x for x in steps if x <= max(steps[0], steps[-1] * fraction))
        governor = "simple_ondemand" if domain == "gpu" else ("performance" if mode == "performance" else "schedutil")
        changes += ([("gpu.max", maximum)] if domain == "gpu" else
                    [(f"{domain}.min", steps[0]), (f"{domain}.max", maximum), (f"{domain}.governor", governor)])
    return changes


class Hardware:
    """Discover exact board interfaces, then address a closed set of logical keys."""
    def __init__(self, root=Path("/sys")):
        self.root = Path(root)
        self.portal = Portal(self.root)
        if self.portal.text(self.root / "firmware/devicetree/base/model") != MODEL:
            raise Refused("Controls require an AYN Odin 2 Portal")
        self.paths = {}
        self.domains = {}
        self.indices = {}
        for policy, cpus in {"policy0": "0 1 2", "policy3": "3 4 5 6", "policy7": "7"}.items():
            path = self.root / "devices/system/cpu/cpufreq" / policy
            if self.portal.text(path / "scaling_driver") != "qcom-cpufreq-hw" or " ".join(
                    (self.portal.text(path / "related_cpus") or "").split()) != cpus:
                raise Refused("Unexpected Portal CPU topology or driver")
            steps = self._steps(path / "scaling_available_frequencies")
            governors = (self.portal.text(path / "scaling_available_governors") or "").split()
            if not {"schedutil", "performance"} <= set(governors):
                raise Refused("Required CPU governors are unavailable")
            self.domains[policy] = {"steps": steps, "governors": governors}
            for key, name in {"min": "scaling_min_freq", "max": "scaling_max_freq", "governor": "scaling_governor"}.items():
                self.paths[f"{policy}.{key}"] = path / name
        gpu = self.root / "class/devfreq/3d00000.gpu"
        self.domains["gpu"] = {"steps": self._steps(gpu / "available_frequencies"),
                               "governors": (self.portal.text(gpu / "available_governors") or "").split()}
        if "simple_ondemand" not in self.domains["gpu"]["governors"]:
            raise Refused("Unexpected GPU governor interface")
        # min_freq is an effective QoS constraint and can change under a DRM
        # client's boost request. Leave GPU minimum/governor ownership alone.
        self.paths["gpu.max"] = gpu / "max_freq"
        fans = [p for p in (self.root / "class/hwmon").glob("hwmon*") if self.portal.text(p / "name") == "pwmfan"]
        if len(fans) != 1:
            raise Refused("Expected exactly one pwmfan")
        self.paths["fan.pwm"] = fans[0] / "pwm1"
        self.paths["fan.enable"] = fans[0] / "pwm1_enable"
        self.rpm_path = fans[0] / "fan1_input"
        for side in "lr":
            for index in range(1, 5):
                key = f"{side}{index}"
                path = self.root / "class/leds" / f"rgb:{key}"
                order = (self.portal.text(path / "multi_index") or "").split()
                if sorted(order) != ["blue", "green", "red"] or self.portal.text(path / "max_brightness") != "255":
                    raise Refused("Unexpected multicolor LED layout")
                self.indices[key] = order
                self.paths[f"{key}.color"] = path / "multi_intensity"
                self.paths[f"{key}.brightness"] = path / "brightness"
        # Resolve links once to the kernel's devices tree; clients cannot supply paths.
        if self.root == Path("/sys"):
            for path in self.paths.values():
                if not path.resolve(strict=True).is_relative_to(Path("/sys/devices")):
                    raise Refused("Hardware path escaped the sysfs devices tree")
        for key in self.paths:
            self.validate(key, self.read(key))

    def _steps(self, path):
        try:
            values = sorted(set(int(x) for x in (self.portal.text(path) or "").split()))
        except ValueError as error:
            raise Refused("Malformed clock steps") from error
        if not values or values[0] <= 0:
            raise Refused("Clock steps are unavailable")
        return values

    def read(self, key):
        value = self.portal.text(self.paths[key])
        if value is None:
            raise Refused(f"Cannot read {key}")
        return " ".join(value.split())

    def validate(self, key, value):
        if key not in self.paths:
            raise Refused("Unknown hardware field")
        group, field = key.split(".")
        if group in self.domains:
            if field == "governor":
                if value not in self.domains[group]["governors"]:
                    raise Refused("Unavailable governor")
            elif value not in [str(x) for x in self.domains[group]["steps"]]:
                raise Refused("Frequency is not an advertised clock step")
        elif group == "fan":
            integer(int(value), 0, 255 if field == "pwm" else 3)
        elif field == "color":
            parts = value.split()
            if len(parts) != 3:
                raise Refused("Expected three LED channels")
            for part in parts:
                integer(int(part), 0, 255)
        else:
            integer(int(value), 0, 255)

    def write(self, key, value):
        value = str(value)
        self.validate(key, value)
        # One sysfs write, followed by authoritative readback.
        with self.paths[key].open("w", encoding="ascii") as stream:
            stream.write(value + "\n")
        # CPUFreq QoS updates can schedule a worker after the sysfs write returns.
        # Wait for the requested limit, rather than mistaking the old value for
        # rejection or claiming success before the worker applies it.
        deadline = time.monotonic() + 0.35
        actual = self.read(key)
        while actual != value and time.monotonic() < deadline:
            time.sleep(0.01)
            actual = self.read(key)
        if actual != value:
            raise Refused(f"Hardware did not accept {key}: requested {value}, read {actual}")

    def temperatures(self):
        values = self.portal.thermals()
        return values["cpu_c"], values["gpu_c"]

    def rpm(self):
        return self.portal.number(self.rpm_path)

    def fan_owner(self):
        """'kernel' when a thermal zone drives the fan (mainline DT), else 'helper'."""
        for zone in (self.root / "class/thermal").glob("thermal_zone*"):
            for link in zone.glob("cdev[0-9]*"):
                if link.is_symlink() and self.portal.text(link / "type") == "pwm-fan":
                    return "kernel"
        return "helper"

    def claimable(self, group):
        if group == "fan":
            if self.fan_owner() == "kernel":
                raise Refused("The kernel thermal controller owns this fan")
            if self.read("fan.enable") != "1":
                raise Refused("Fan enable mode changed; refusing competing control")
        if group in {"left", "right"}:
            for key in self.keys(group):
                trigger = self.paths[key].parent / "trigger"
                if "[none]" not in (self.portal.text(trigger) or ""):
                    raise Refused("An LED trigger owns this ring")

    def keys(self, group):
        if group == "power":
            return [f"{domain}.{field}" for domain in self.domains
                    for field in (("max",) if domain == "gpu" else ("min", "max", "governor"))]
        if group == "fan":
            return ["fan.pwm", "fan.enable"]
        if group not in {"left", "right"}:
            raise Refused("Unknown control group")
        return [f"{group[0]}{i}.{field}" for i in range(1, 5) for field in ("color", "brightness")]


class Engine:
    TTL = 10

    def __init__(self, hardware, state_path, boot_id, clock=lambda: time.clock_gettime(time.CLOCK_BOOTTIME)):
        self.hw, self.state_path, self.boot_id, self.clock = hardware, Path(state_path), boot_id, clock
        self.groups = {}
        self.owner = None
        self.deadline = 0
        self.last_tick = clock()
        self.fan_mode = None
        self.fan_percent = 30
        self.power_mode = None
        self.error = ""
        self.stall_ticks = 0
        self.saved_state = None
        self.expected = {}
        if self.state_path.exists():
            state = json.loads(self.state_path.read_text())
            if state.get("boot_id") == boot_id:
                self.groups = state["groups"]
                # Journal keys are never interpreted as paths or code.
                for group, entries in self.groups.items():
                    if set(entries) != set(self.hw.keys(group)):
                        raise Refused("Invalid recovery journal")
                    for key, entry in entries.items():
                        self.hw.validate(key, entry["before"])
                        for value in entry["allowed"]:
                            self.hw.validate(key, value)
                self.restore()
            else:
                self.save()  # Never replay a prior boot's hardware state.

    def save(self):
        serialized = json.dumps({"boot_id": self.boot_id, "groups": self.groups}, allow_nan=False, sort_keys=True)
        if serialized == self.saved_state:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = self.state_path.with_suffix(".tmp")
        fd = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.state_path)
        directory = os.open(self.state_path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        self.saved_state = serialized

    def claim(self, token, groups):
        if self.owner is not None and self.owner != token:
            raise Refused("Another panel has the control lease")
        if self.owner is None and self.groups:
            raise Refused("Previous settings are still being recovered")
        for group in groups:
            self.hw.claimable(group)
            if group in self.groups and not self.consistent(group):
                raise Refused(f"External changes detected in {group}; restore before continuing")
        for group in groups:
            if group not in self.groups:
                self.groups[group] = {key: {"before": self.hw.read(key), "allowed": [self.hw.read(key)]}
                                      for key in self.hw.keys(group)}
                self.expected.update({key: entry["before"] for key, entry in self.groups[group].items()})
        self.save()
        self.owner, self.deadline = token, self.clock() + self.TTL

    def plan(self, group, changes):
        for key, value in changes:
            self.hw.validate(key, str(value))
            allowed = self.groups[group][key]["allowed"]
            if str(value) not in allowed:
                allowed.append(str(value))
        self.save()  # Persist the complete transaction BEFORE its first write.

    def apply(self, group, changes):
        self.plan(group, changes)
        for key, value in changes:
            self.write_owned(key, value)

    def write_owned(self, key, value):
        self.expected[key] = {self.hw.read(key), str(value)}
        self.hw.write(key, value)
        self.expected[key] = str(value)

    def consistent(self, group):
        return all(self.hw.read(key) in self.expected[key] if isinstance(self.expected.get(key), set) else
                   self.hw.read(key) == self.expected[key] if key in self.expected else
                   self.hw.read(key) in entry["allowed"] for key, entry in self.groups[group].items())

    def power_changes(self, mode):
        return plan_power(self.hw.domains, mode)

    def request(self, request):
        if not isinstance(request, dict) or not isinstance(request.get("op"), str):
            raise Refused("Expected a control request")
        op, token = request["op"], request.get("token", "")
        fields = {"status": set(), "restore": set(), "fan": {"mode", "percent"},
                  "power": {"mode"}, "rgb": {"side", "red", "green", "blue", "brightness"}}
        if op not in fields or set(request) - ({"op", "token"} | fields[op]):
            raise Refused("Unknown operation or fields")
        if not isinstance(token, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{20,100}", token):
            raise Refused("Invalid session token")
        if self.owner == token:
            self.deadline = self.clock() + self.TTL
        if op == "status":
            return self.status(token)
        if op == "restore":
            if self.owner not in {None, token}:
                raise Refused("Another panel owns these settings")
            self.restore()
            return self.status(token)
        if op == "power":
            changes = self.power_changes(request.get("mode"))
            self.claim(token, ["power"])
            try:
                self.apply("power", changes)
                self.power_mode = request["mode"]
            except Exception:
                self.restore()
                raise
        elif op == "fan":
            mode = request.get("mode")
            if mode not in {"auto", "manual", "max"}:
                raise Refused("Unknown fan mode")
            percent = integer(request.get("percent", 30), 30, 100)
            self.claim(token, ["fan"])
            # Predeclare every value an automatic fan loop may produce; no per-tick flash writes.
            self.plan("fan", [("fan.pwm", x) for x in range(77, 256)])
            self.fan_mode, self.fan_percent = mode, percent
            try:
                self.fan_tick()
            except Exception:
                self.restore()
                raise
        else:
            side = request.get("side")
            if side not in {"left", "right", "both"}:
                raise Refused("Unknown joystick ring")
            color = {key: integer(request.get(key), 0, 255) for key in ("red", "green", "blue")}
            brightness = integer(request.get("brightness"), 0, 255)
            groups = ["left", "right"] if side == "both" else [side]
            self.claim(token, groups)
            try:
                for group in groups:
                    changes = []
                    for i in range(1, 5):
                        key = f"{group[0]}{i}"
                        value = " ".join(str(color[channel]) for channel in self.hw.indices[key])
                        changes += [(f"{key}.color", value), (f"{key}.brightness", brightness)]
                    self.apply(group, changes)
            except Exception:
                self.restore()
                raise
        self.error = ""
        return self.status(token)

    def status(self, token):
        return {"available": True, "owned": self.owner == token,
                "occupied": self.owner is not None and self.owner != token,
                "fan_mode": self.fan_mode, "fan_percent": self.fan_percent, "fan_owner": self.hw.fan_owner(),
                "power_mode": self.power_mode, "changed_groups": list(self.groups),
                "recovering": self.owner is None and bool(self.groups), "error": self.error,
                "rings": {key: {"channels": dict(zip(self.hw.indices[key], map(int, self.hw.read(key + ".color").split()))),
                                "brightness": int(self.hw.read(key + ".brightness"))} for key in self.hw.indices}}

    def hot(self):
        cpu, gpu = self.hw.temperatures()
        return cpu is None or gpu is None or max(cpu, gpu) >= 85

    def fan_tick(self):
        if "fan" not in self.groups:
            return
        if not self.consistent("fan"):
            raise Refused("Fan settings changed outside this panel")
        cpu, gpu = self.hw.temperatures()
        hot = cpu is None or gpu is None or max(cpu, gpu) >= 85
        rpm = self.hw.rpm()
        self.stall_ticks = self.stall_ticks + 1 if rpm == 0 else 0
        if hot or self.stall_ticks >= 5 or self.owner is None or self.fan_mode == "max":
            percent = 100
        elif self.fan_mode == "manual":
            percent = self.fan_percent
        else:
            temperature = max(cpu, gpu)
            percent = min(100, max(30, round(30 + (temperature - 45) * 70 / 40)))
        target = max(77, round(percent * 255 / 100))
        if self.hw.read("fan.pwm") != str(target):
            self.write_owned("fan.pwm", target)

    def restore(self):
        self.owner = None
        self.fan_mode = self.power_mode = None
        errors = []
        for group in list(self.groups):
            try:
                if not self.consistent(group):
                    # Yield to another writer; never overwrite its newer choices.
                    errors.append(f"Preserved external changes to {group}")
                    del self.groups[group]
                    continue
                if group == "fan" and self.hot():
                    self.plan("fan", [("fan.pwm", 255)])
                    self.write_owned("fan.pwm", 255)
                    errors.append("Fan recovery waits for valid temperatures below 85°C")
                    continue
                entries = self.groups[group]
                if group == "power":
                    changes = []
                    for domain, spec in self.hw.domains.items():
                        if domain == "gpu":
                            changes.append(("gpu.max", entries["gpu.max"]["before"]))
                            continue
                        changes += [(f"{domain}.min", spec["steps"][0]),
                                    (f"{domain}.max", entries[f"{domain}.max"]["before"]),
                                    (f"{domain}.min", entries[f"{domain}.min"]["before"]),
                                    (f"{domain}.governor", entries[f"{domain}.governor"]["before"])]
                else:
                    changes = [(key, entry["before"]) for key, entry in entries.items()]
                self.apply(group, changes)
                del self.groups[group]
            except (OSError, ValueError) as error:
                errors.append(f"{group}: {error}")
        self.save()
        self.error = "; ".join(errors)

    def tick(self):
        now = self.clock()
        resumed = now - self.last_tick > 5
        self.last_tick = now
        if self.owner and (now > self.deadline or resumed):
            self.restore()
        elif not self.owner and self.groups:
            self.restore()
        elif self.fan_mode:
            try:
                self.fan_tick()
            except (OSError, ValueError) as error:
                self.error = str(error)
                self.restore()
