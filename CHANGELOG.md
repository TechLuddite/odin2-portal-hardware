# Changelog

## 0.2.1 — local inspection bridge

- Export the actual panel's bounded QML scene as JSON through existing IPC.
- Add explicit panel navigation without arbitrary clicks, evaluation or hardware
  writes, plus live terminal watching through the Portal project.
- Show applied ring colors/brightness separately from the next color selection.

## 0.2.0 — local control build

- Add session fan Auto/Manual/Maximum, guarded Linux power presets and static
  left/right joystick RGB controls using reported channel order.
- Add explicit root-owned helper installation, UID-authenticated Unix socket,
  verified writes, lease expiry and same-boot transaction recovery.
- Keep monitoring unprivileged; add control-engine tests and real-Ui fixtures.
- Physical load/color/resume acceptance and hosted security review remain open.

## 0.1.0 — unreleased

- Standalone Omarchy service and bar panel for the AYN Odin 2 Portal.
- Read-only CPU/GPU clocks/governors, hottest CPU/GPU temperatures, fan RPM/PWM,
  named thermal sensors and battery telemetry.
- Explicit unsupported, missing-data and stale-read states.
- Synthetic sysfs tests and isolated QML/media fixtures.
- Luddite-style repository checks, pinned Scout/baseline CI and provenance docs.

Power presets, fan curves and charge-limit controls are planned work, not
features of this version.
