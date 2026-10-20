#!/usr/bin/env python3
"""Explicit root installation; review this source before running it.

Usage: sudo python3 -I -B system/install-helper.py --user YOUR_USERNAME
Copies a closed file list; the daemon never imports user-writable plugin code.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--user", required=True)
args = parser.parse_args()
if os.getuid() != 0:
    parser.error("Root is required for the separate system helper installation")
account = pwd.getpwnam(args.user)
if not 1000 <= account.pw_uid <= 60000 or Path("/sys/firmware/devicetree/base/model").read_text().rstrip("\0\n") != "AYN Odin 2 Portal":
    parser.error("Expected the Portal and a regular desktop user")
source = Path(__file__).resolve().parents[1]
destination = Path("/usr/local/lib/odin2-portal-hardware")
unit = Path("/etc/systemd/system/odin2-portal-hardware.service")
bank = Path("/var/lib/odin2-portal-hardware/installations") / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
bank.mkdir(parents=True, mode=0o700)
for path in (destination, unit):
    if path.exists():
        shutil.copytree(path, bank / path.name) if path.is_dir() else shutil.copy2(path, bank / path.name)
files = {"system/daemon.py": "daemon.py", "backend/__init__.py": "backend/__init__.py",
         "backend/portal.py": "backend/portal.py", "backend/controls.py": "backend/controls.py"}
payload = {target: (source / origin).read_bytes() for origin, target in files.items()}
unit_data = (source / "system/odin2-portal-hardware.service").read_text().replace("@UID@", str(account.pw_uid)).replace("@GID@", str(account.pw_gid))
# Validate the engine against the live board before enabling anything; reads only.
import sys
sys.path.insert(0, str(source))
from backend.controls import Hardware
Hardware()
subprocess.run(["systemctl", "stop", "odin2-portal-hardware.service"], check=False)
destination.mkdir(parents=True, exist_ok=True, mode=0o755)
receipt = {}
for name, data in payload.items():
    path = destination / name
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    path.write_bytes(data)
    os.chown(path, 0, 0)
    os.chmod(path, 0o644)
    receipt[name] = hashlib.sha256(data).hexdigest()
unit.write_text(unit_data)
os.chmod(unit, 0o644)
(bank / "receipt.json").write_text(json.dumps({"files": receipt, "uid": account.pw_uid, "gid": account.pw_gid}, indent=2) + "\n")
subprocess.run(["systemctl", "daemon-reload"], check=True)
subprocess.run(["systemctl", "enable", "--now", "odin2-portal-hardware.service"], check=True)
print(json.dumps({"backup": str(bank), "files": receipt}))
