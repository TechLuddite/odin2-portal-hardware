# Changelog

## 0.4.2: startup loop fix

- Fix a startup loop when the kernel owns the fan: the service also required
  a fan mode before treating startup as done, so it reran startup on every
  refresh and kept the controls busy. Power buttons did not respond and the
  refresh indicator flashed.
- Remove the refresh button. Readings refresh on their own.
- Move the remembered-settings note from the panel to the README.
- Add the live UFS storage ceiling to the levels table.
- The startup QML test now requires readiness to hold, and covers the
  kernel-owned fan.

## 0.4.1: kernel fan control and a levels table

- Detect when a kernel thermal zone drives the fan (mainline Linux device
  tree) and report it as `fan_owner`. Startup then restores the power level
  alone and stops retrying the fan, which made power buttons need a second
  press. The saved fan choice is kept for kernels where the helper owns it.
- The Fan tab shows kernel control as information and disables fan modes.
- Replace the power level explanation and preview buttons with one table of
  CPU and GPU ceilings per level, highlighting the active level.

## 0.4.0 — remembered LEDs and theme colors

- Persist each ring's color, brightness, off state and Manual/Follow theme choice.
- Restore after plugin startup and resume within the existing owned session.
- Match light/neutral palettes to white and other accents or explicit stock
  keyboard hints to the nearest existing color; Tokyo Night maps to purple.
- Keep off state and brightness through theme changes and handle replacement of
  the active theme directory. Avoid steady-state writes and blind failure retries.
- Preserve current readback at guarded upgrade, without new root operations.

## 0.3.3 — reliable LED brightness transitions

- Turn selected rings off and confirm all selected groups before applying a
  nonzero color/brightness request through the existing journaled helper API.
- Validate the complete target before any preliminary off operation; stop on
  off-step failure or missing ownership, and report target errors without retry.
- Keep off, status, fan, power and restore requests unchanged. No root helper
  update or new privileged operation is required. A brief off transition is
  expected when applying a nonzero LED setting.

## 0.3.2 — popup theme text

- Use the popup text palette instead of the transparent bar’s adaptive foreground.
- Keep titles, unselected buttons and readings readable with Osaka Jade and
  follow live popup palette changes independently of bar colors.
- Preserve hardware policy, controls and saved choices.

## 0.3.1 — inspect power-level effects

- Preview each power level without applying it: exact advertised CPU ranges and
  ceilings, scaling/performance behavior and unchanged GPU/UFS/fan/RGB fields.
- Show live CPU/GPU/UFS governors and clocks beside the planned settings.
- Flag temperatures at or above the existing 85°C fan safeguard with fan readback.
- Reuse the command planner for previews; no privileged helper or policy change.


## 0.3.0 — startup power/fan preferences and Portal feedback

- Initialize Saver power and Auto fan when no saved choices exist; restore
  validated saved power/fan preferences on subsequent plugin sessions.
- Remember only successful power/fan changes in a private user state file.
- Keep thermal/sensor/stall overrides and explicit release behavior in the
  existing root helper. RGB remains session-only.

- Give Apply color and Lights off visible button borders before interaction.
- Retain the hardware service through unrelated Omarchy plugin rescans, keeping
  its current session token and leases. Explicit disable/removal and shell exit
  still release the service. Portal deployment/acceptance is recorded separately.

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
