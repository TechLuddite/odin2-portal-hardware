"""Unprivileged bounded Unix-socket client. Never launches a privileged command."""
import json
import socket

SOCKET = "/run/odin2-portal-hardware/control.sock"


def exchange(request):
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
