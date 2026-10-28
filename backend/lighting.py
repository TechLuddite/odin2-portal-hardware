"""User LED preferences and theme matching, using only the existing helper API."""
import colorsys
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
import tomllib

COLORS = {"red": [255, 0, 0], "green": [0, 255, 0], "blue": [0, 0, 255],
          "purple": [180, 0, 255], "white": [255, 255, 255]}
SIDES = {"left": "l", "right": "r"}


def location():
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "odin2-portal-hardware/lights.json"


def validate(value):
    if not isinstance(value, dict) or set(value) != {"schema_version", "sides"} or type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("Invalid LED preferences")
    if not isinstance(value["sides"], dict) or not set(value["sides"]) <= set(SIDES):
        raise ValueError("Invalid LED sides")
    for side in value["sides"].values():
        if not isinstance(side, dict) or set(side) != {"mode", "enabled", "red", "green", "blue", "brightness"} or side["mode"] not in {"manual", "theme"} or type(side["enabled"]) is not bool:
            raise ValueError("Invalid LED mode")
        if any(type(side[k]) is not int or not 0 <= side[k] <= 255 for k in ("red", "green", "blue", "brightness")):
            raise ValueError("Invalid LED channels")
    return value


def load(path):
    try:
        info = path.lstat()
        if path.is_symlink() or info.st_uid != os.getuid() or info.st_size > 2048:
            raise ValueError("Unsafe LED preferences")
        return validate(json.loads(path.read_text()))
    except (OSError, ValueError, KeyError, TypeError):
        return {"schema_version": 1, "sides": {}}


def save(path, value):
    validate(value)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.is_symlink() or path.parent.stat().st_uid != os.getuid() or path.is_symlink():
        raise ValueError("Unsafe LED preferences directory")
    path.parent.chmod(0o700)
    fd, name = tempfile.mkstemp(prefix=".lights-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as out:
            json.dump(value, out)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def theme_color(current=None, stock=None):
    """Read a complete palette afresh, surviving replacement of current/theme."""
    current = current or Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "omarchy/current/theme"
    stock = stock or Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "themes"
    try:
        data = (current / "colors.toml").read_bytes()
        if len(data) > 32768:
            return None
        palette = tomllib.loads(data.decode())
        accent = palette["accent"]
        if not isinstance(accent, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
            return None
        # Prefer an explicit packaged keyboard RGB hint when the active palette
        # matches that stock theme. Never trust a stale generated current hint.
        hint = accent
        for folder in sorted(stock.iterdir()):
            if (folder / "colors.toml").read_bytes() == data:
                keyboard = folder / "keyboard.rgb"
                if keyboard.is_file():
                    candidate = keyboard.read_text().strip().lstrip("#")
                    if re.fullmatch(r"[0-9a-fA-F]{6}", candidate):
                        hint = "#" + candidate
                break
        rgb = [int(hint[i:i+2], 16) / 255 for i in (1, 3, 5)]
        hue, saturation, _ = colorsys.rgb_to_hsv(*rgb)
        if palette.get("mode") == "light" or saturation < 0.18:
            return "white"
        def distance(name):
            other = colorsys.rgb_to_hsv(*(v / 255 for v in COLORS[name]))[0]
            delta = abs(hue - other)
            return min(delta, 1 - delta)
        return min((name for name in COLORS if name != "white"), key=distance)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def observed(current, side, mode="manual"):
    rings = current.get("rings", {})
    groups = [rings.get(SIDES[side] + str(i)) for i in range(1, 5)]
    if not groups[0] or any(group != groups[0] for group in groups):
        return None  # Never flatten mixed/unreadable groups into a guessed value.
    brightness = groups[0].get("brightness")
    value = dict(groups[0].get("channels", {}), brightness=brightness, enabled=type(brightness) is int and brightness > 0, mode=mode)
    try:
        validate({"schema_version": 1, "sides": {side: value}})
        return value
    except (ValueError, TypeError):
        return None


def target(value, color):
    result = dict(value)
    if value["mode"] == "theme" and color:
        result.update(zip(("red", "green", "blue"), COLORS[color]))
    return result


def request_for(side, value, token):
    return dict(op="rgb", side=side, token=token,
                **{key: value[key] for key in ("red", "green", "blue")},
                brightness=value["brightness"] if value["enabled"] else 0)


def matches(current, side, value):
    actual = observed(current, side, value["mode"])
    return bool(actual and all(actual[k] == value[k] for k in ("red", "green", "blue"))
                and actual["brightness"] == (value["brightness"] if value["enabled"] else 0))


def describe(current, path, color):
    value = load(path)
    ready = bool(current.get("owned") and not current.get("error") and not current.get("recovering"))
    return dict(value, theme_color=color, needs_sync=ready and any(
        not matches(current, side, target(saved, color)) for side, saved in value["sides"].items()))


def apply(exchange, request, path, color=None):
    """Serialize read/apply/save with manual actions and theme synchronization."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.is_symlink() or path.parent.stat().st_uid != os.getuid():
        raise ValueError("Unsafe LED preferences directory")
    fd = os.open(path.with_suffix(".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _apply(exchange, request, path, color)


def _apply(exchange, request, path, color):
    op = request.get("op")
    allowed = {"rgb": {"op", "side", "token", "red", "green", "blue", "brightness"},
               "lighting": {"op", "side", "token", "mode", "brightness"},
               "lights-off": {"op", "side", "token"}, "sync-lights": {"op", "token"}}
    if op not in allowed or set(request) - allowed[op] or not {"op", "token"} <= set(request):
        return {"error": "Invalid LED request"}
    token = request["token"]
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{20,100}", token):
        return {"error": "Invalid LED session"}
    if op != "sync-lights" and request.get("side") not in {"left", "right", "both"}:
        return {"error": "Invalid LED side"}
    if op == "rgb" and (set(request) != allowed[op] or any(type(request[k]) is not int or not 0 <= request[k] <= 255 for k in ("red", "green", "blue", "brightness"))):
        return {"error": "Invalid LED channels"}
    if op == "lighting" and (request.get("mode") not in {"theme", "manual"} or ("brightness" in request and (type(request["brightness"]) is not int or not 0 <= request["brightness"] <= 255))):
        return {"error": "Invalid LED mode or brightness"}
    current = exchange({"op": "status", "token": token})
    if not current.get("owned") or current.get("error") or current.get("recovering"):
        return dict(current, error=current.get("error") or "LED session is not ready")
    prefs = load(path)
    sides = list(SIDES) if op == "sync-lights" or request.get("side") == "both" else [request["side"]]
    for side in sides:
        saved = prefs["sides"].get(side)
        value = dict(saved) if saved else observed(current, side)
        if value and not value["enabled"] and value["brightness"] == 0:
            value["brightness"] = 128
        if op == "sync-lights" and not saved:
            continue  # No saved state: leave hardware untouched until adopted/chosen.
        if op == "rgb":
            value = dict(mode="manual", enabled=request["brightness"] > 0,
                         **{k: request[k] for k in ("red", "green", "blue")},
                         brightness=request["brightness"] or (saved or {}).get("brightness", 128))
        elif value is None:
            return dict(current, error="Ring groups differ; apply a manual color first")
        elif op == "lights-off":
            value["enabled"] = False
        elif op == "lighting":
            value["mode"] = request["mode"]
            if "brightness" in request:
                value["enabled"] = request["brightness"] > 0
                if request["brightness"] > 0:
                    value["brightness"] = request["brightness"]
        value = target(value, color)
        if op == "lighting" and value["mode"] == "theme" and color is None:
            return dict(current, error="Theme colors are temporarily unavailable")
        if not matches(current, side, value):
            current = exchange(request_for(side, value, token))
            if current.get("error") or not current.get("owned") or not matches(current, side, value):
                return dict(current, error=current.get("error") or "LED readback did not match; settings were not saved")
        prefs["sides"][side] = value
        if saved != value:
            save(path, prefs)
    return dict(current, lighting=describe(current, path, color))


def adopt(current, path, mode="theme"):
    """Seed missing preferences during a guarded upgrade, without LED writes."""
    value = load(path)
    for side in SIDES:
        if side not in value["sides"]:
            actual = observed(current, side, mode)
            if actual:
                if not actual["enabled"]:
                    actual["brightness"] = 128  # Initial off state has no readable previous intensity.
                value["sides"][side] = actual
    save(path, value)
