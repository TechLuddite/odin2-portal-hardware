# Security policy

## Current capability boundary

The monitoring adapter remains read-only. QML uses explicit Python argv,
bounded JSON and timeouts. The optional control helper is an explicit root
installation, not an automatic plugin install hook. It copies only reviewed
engine/telemetry/daemon files into a root-owned directory; runtime imports never
use the user's plugin directory. It has no shell-execution or arbitrary-path API.

The Unix socket accepts only the configured desktop UID, checked with Linux
SO_PEERCRED. Requests are bounded to 8 KiB, have socket deadlines and closed
operation schemas. Operations select Linux power presets, guarded fan modes,
static ring colors/brightness, status/heartbeat, or restoration. Values are
validated against discovered clock steps and channel order. No network listener,
input/audio device access, sudoers policy, global sysfs chmod, package action,
boot action, charging policy, fan-off or overclocking endpoint exists.

A single session lease, verified writes and a root-only recovery journal limit
partial failures. Kernel thermal fan ownership and active LED triggers are
refused. Fan control has a 30% floor and a full-speed response to high/missing
CPU/GPU temperatures or sustained zero RPM. Panel loss and suspend gaps restore
prior settings; hot fan recovery is deferred with full cooling. Firmware,
sensors, fan hardware, another privileged writer and a compromised desktop UID
remain outside this boundary. An active hardware failure is not made safe merely
by successful sysfs readback.

The plugin shares Omarchy's unsandboxed shell process. Review capabilities for
privileged installation and system-service management are intentional and must
be reviewed honestly; pinned CI scans retain their strict findings/capability
gates. Local tests are not marketplace verification or hosted-CI acceptance.

## Private reports

When the repository is published, use GitHub's private vulnerability reporting
for this project. If it is not enabled, contact the maintainer privately before
sharing exploit details. Do not post credentials, private device state or
security exploit details in public issues.

Include the affected version/commit, impact, minimal reproduction and any
proposed fix. Test only authorized systems and redact personal information.
Private collaboration can be arranged through a security advisory after triage.
Reports do not grant repository write access. No response deadline, bounty or
fix guarantee is promised.
