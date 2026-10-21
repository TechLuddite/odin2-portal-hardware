"""User-owned power/fan choices; validated before the existing helper is called."""
import json
import fcntl
import os
from pathlib import Path
import tempfile
import re
import time

DEFAULT = {"schema_version": 1, "power": "saver", "fan": "auto", "fan_percent": 40}


def validate(value):
    if not isinstance(value, dict) or set(value) != set(DEFAULT) or type(value.get("schema_version")) is not int or value.get("schema_version") != 1:
        raise ValueError("Invalid saved power/fan preferences")
    if value["power"] not in {"saver", "balanced", "performance"} or value["fan"] not in {"auto", "manual", "max"}:
        raise ValueError("Invalid saved power/fan mode")
    if type(value["fan_percent"]) is not int or not 30 <= value["fan_percent"] <= 100:
        raise ValueError("Invalid saved fan percentage")
    return dict(value)


def location():
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "odin2-portal-hardware/power-fan.json"


def load(path):
    try:
        if path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_size > 2048:
            raise ValueError("Unsafe preferences file")
        return validate(json.loads(path.read_text())), "saved"
    except FileNotFoundError:
        return dict(DEFAULT), "defaults"
    except (OSError, ValueError, KeyError, TypeError):
        return dict(DEFAULT), "invalid-saved-defaults"


def save(path, value):
    value = validate(value)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.is_symlink() or path.parent.stat().st_uid != os.getuid() or path.is_symlink():
        raise ValueError("Unsafe preferences directory")
    path.parent.chmod(0o700)
    fd, name = tempfile.mkstemp(prefix=".power-fan-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as out:
            json.dump(value, out)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def remember(path, request, result):
    if result.get("error") or not result.get("owned") or request.get("op") not in {"power", "fan"}:
        return
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_fd = os.open(path.with_suffix('.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        value, _ = load(path)
        if request["op"] == "power":
            value["power"] = result["power_mode"]
        else:
            value["fan"], value["fan_percent"] = result["fan_mode"], result["fan_percent"]
        save(path, value)


def initialize(exchange, token, path):
    preferences, origin = load(path)
    current = exchange({"op": "status", "token": token})
    if not current.get("available") or current.get("occupied") or current.get("recovering") or current.get("error"):
        return dict(current, startup="waiting", preference_source=origin)
    # A valid active session is already initialized; never reset a user's newer choice.
    if current.get("owned") and current.get("fan_mode") and current.get("power_mode"):
        return dict(current, startup="ready", preference_source=origin)
    requests = [{"op": "fan", "mode": preferences["fan"], "percent": preferences["fan_percent"], "token": token},
                {"op": "power", "mode": preferences["power"], "token": token}]
    for request in requests:
        current = exchange(request)
        if not current.get("owned") or current.get("error"):
            # A failed power transaction may restore all groups. Re-establish
            # safe Auto fan independently, then retry the whole startup later.
            if request["op"] == "power":
                exchange({"op": "fan", "mode": "auto", "percent": 40, "token": token})
            return dict(current, startup="waiting", preference_source=origin)
    return dict(current, startup="ready", preference_source=origin)


def handoff_location():
    return Path(os.environ.get("XDG_RUNTIME_DIR", "/run/user/%s" % os.getuid())) / "odin2-portal-hardware-handoff.json"


def adopt_session(exchange, path, preferences_path, boot_id, now=None):
    """Consume a short-lived, same-user upgrade handoff; never acquire a lease."""
    now = time.time() if now is None else now
    result = {"adopted": False}
    try:
        info = path.lstat()
        if path.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size > 2048:
            return result
        # The installer creates this file once, immediately before a guarded reload.
        value = json.loads(path.read_text())
        path.unlink()
        token = value.get("token", "")
        if (not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{20,100}", token)
            or value.get("boot_id") != boot_id or not isinstance(value.get("created_at"), (int, float))
            or not 0 <= now - value["created_at"] <= 30):
            return result
        current = exchange({"op": "status", "token": token})
        if not current.get("owned") or current.get("error"):
            return result
        save(preferences_path, dict(DEFAULT, power=current["power_mode"],
                                   fan=current["fan_mode"], fan_percent=current["fan_percent"]))
        return {"adopted": True, "token": token}
    except (OSError, ValueError, KeyError, TypeError):
        return result
