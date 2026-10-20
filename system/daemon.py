#!/usr/bin/env python3
"""Root-owned, local-only Portal helper. Not loaded from the user's plugin tree."""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import struct
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend.controls import Engine, Hardware, Refused


def serve(uid):
    if os.getuid() != 0:
        raise Refused("Run the installed helper as root through systemd")
    engine = Engine(Hardware(), Path("/var/lib/odin2-portal-hardware/session.json"),
                    Path("/proc/sys/kernel/random/boot_id").read_text().strip())
    running = True
    def stop(signum, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    path = Path("/run/odin2-portal-hardware/control.sock")
    path.unlink(missing_ok=True)
    with socket.socket(socket.AF_UNIX) as server:
        server.bind(str(path))
        os.chown(path, 0, os.getgid())
        os.chmod(path, 0o660)
        server.listen(8)
        server.settimeout(0.5)
        next_tick = time.monotonic()
        try:
            while running:
                if time.monotonic() >= next_tick:
                    engine.tick()
                    next_tick = time.monotonic() + 1
                try:
                    connection, _ = server.accept()
                except TimeoutError:
                    continue
                with connection:
                    connection.settimeout(0.2)
                    try:
                        _, peer_uid, _ = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                        if peer_uid != uid:
                            raise Refused("This socket is reserved for the configured desktop user")
                        data = bytearray()
                        while b"\n" not in data and len(data) <= 8192:
                            part = connection.recv(4096)
                            if not part:
                                break
                            data.extend(part)
                        if len(data) > 8192:
                            raise Refused("Control request too large")
                        result = engine.request(json.loads(data))
                    except (ValueError, OSError, KeyError, TypeError) as error:
                        result = {"available": True, "error": str(error)}
                    try:
                        connection.sendall(json.dumps(result, allow_nan=False).encode() + b"\n")
                    except OSError:
                        pass
        finally:
            engine.restore()
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uid", required=True, type=int)
    args = parser.parse_args()
    if not 1000 <= args.uid <= 60000:
        parser.error("Expected a regular desktop UID")
    serve(args.uid)
