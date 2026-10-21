"""Unprivileged bounded Unix-socket client. Never launches a privileged command."""
import json
import re
import socket

SOCKET = "/run/odin2-portal-hardware/control.sock"


def _exchange(request):
    encoded = json.dumps(request, allow_nan=False, separators=(",", ":")).encode() + b"\n"
    if len(encoded) > 8192:
        return {"available": False, "error": "Control request too large"}
    try:
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(8)
            connection.connect(SOCKET)
            connection.sendall(encoded)
            chunks = bytearray()
            while b"\n" not in chunks and len(chunks) <= 8192:
                part = connection.recv(4096)
                if not part:
                    break
                chunks.extend(part)
            if len(chunks) > 8192:
                raise ValueError("Control response too large")
            return json.loads(chunks)
    except (OSError, ValueError) as error:
        return {"available": False, "error": "Portal control helper unavailable: " + str(error)}


def exchange(request):
    # A multicolor update queues work at the old brightness. On this Portal,
    # changing brightness immediately afterwards can leave that old value in
    # place. Use two acknowledged existing operations: off, then the requested
    # color/brightness. The root helper journals both; no new privileged API.
    # Validate the whole request before substituting zero, so an invalid target
    # cannot turn a working ring off before the helper refuses it.
    rgb = (isinstance(request, dict)
           and set(request) == {"op", "token", "side", "red", "green", "blue", "brightness"}
           and request.get("op") == "rgb"
           and isinstance(request.get("token"), str)
           and re.fullmatch(r"[a-zA-Z0-9_-]{20,100}", request["token"])
           and isinstance(request.get("side"), str) and request["side"] in {"left", "right", "both"}
           and all(type(request[key]) is int and 0 <= request[key] <= 255
                   for key in ("red", "green", "blue", "brightness")))
    if rgb and request["brightness"] > 0:
        off = _exchange(dict(request, brightness=0))
        if off.get("error") or not off.get("available") or not off.get("owned"):
            return dict(off, error=off.get("error") or "Could not confirm the LED off step")
        sides = "lr" if request["side"] == "both" else request["side"][0]
        if any(off.get("rings", {}).get(f"{side}{index}", {}).get("brightness") != 0
               for side in sides for index in range(1, 5)):
            return dict(off, error="LEDs did not settle off; requested brightness was not applied")
    return _exchange(request)
