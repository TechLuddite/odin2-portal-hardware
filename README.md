# Odin2 Portal Hardware

A native Omarchy hardware panel for the **AYN Odin 2 Portal**. It shows the
hottest CPU/GPU sensors, fan RPM and PWM duty, CPU/GPU clocks and governors,
and battery status, power and temperature.

![Odin2 Portal Hardware overview in Hackerman, with synthetic readings](preview.png)

Built on [Omarchy](https://github.com/omacom/omarchy)'s actual Commons/Ui kit.
The device-control design research credits MaSi/SteamOS-Ubuntu, Basit and
Hooandee's Panel de Control. Related Omarchy panels informed the design review;
this implementation contains no copied Decky power/fan code. See
[credits and provenance](THIRD_PARTY.md).

## Development status

Version 0.4.1 is a local development build with monitoring and **Power, Fan
and Lights** controls. Power presets use advertised Linux CPU/GPU clock steps;
they are not claimed to reproduce Android's original performance modes. Fan
control offers Auto, Manual (30–100% duty) and Maximum. Static RGB colors and
brightness can be applied to either joystick ring or both. Nonzero RGB updates
first turn the selected rings off, confirm that state, then apply the requested
color and brightness through the existing helper. This avoids an observed
queued color/brightness update race; a brief off transition is expected. Charge limits are
not implemented.

The target is the **Portal**, rather than every device with an ARM CPU or
Snapdragon 8 Gen 2. Other models show an unsupported-device message. Missing
readings appear as `—`; real zero readings stay zero. CPU temperature uses the
hottest relevant CPU sensor rather than averaging it with cooler components.

## Requirements

- Omarchy Quattro, Quickshell and its current Commons/Ui components.
- AYN Odin 2 Portal running Linux with the expected CPUFreq/devfreq, thermal,
  pwm-fan and battery interfaces.
- `/usr/bin/python3`, version 3.11 or newer; standard library only.

Monitoring needs no root helper. Controls require the separately installed,
root-owned local helper described below; no network service is opened. Kernel-exposed readings are not a calibration
guarantee; missing or implausible sensor values remain unavailable.

## Local development installation

The repository has not been published. Local test installation is recorded separately; see [the installation record](docs/development.md#october-20-local-portal-test-installation).
Validate a checkout before another local installation:

```sh
omarchy plugin validate .
python3 -B -m unittest discover -s tests -v
python3 -B tests/qml_smoke.py
```

For a deliberate local installation, copy the source directory into
`~/.config/omarchy/plugins/io.github.techluddite.odin2-portal-hardware/`, excluding
`.git`, `private` and development previews. Then:

```sh
omarchy-shell shell rescanPlugins
omarchy plugin enable io.github.techluddite.odin2-portal-hardware
```

The widget belongs in the bar's right section by default. Left-click opens the
panel; right-click refreshes. Escape closes the panel. **Overview**, **Controls** and **Details** separate summary values, hardware
controls, per-policy CPU/GPU readings and named thermal sensors. The body scrolls when available screen height requires it.

The shared service refreshes every 15 seconds with panels closed and every
three seconds while initializing, open or holding a hardware lease. Loading the
enabled plugin restores saved power/fan choices, or applies Saver and Auto when
none exist. Opening the popup does not change those choices.
On a read failure, the panel marks retained readings as stale and reports the
error. The reader has a five-second timeout; disabling/removing the plugin
ends monitoring and expires the control lease.

## Hardware helper and recovery

Review [the security boundary](SECURITY.md) and the source under `system/` and
`backend/controls.py`, then install explicitly on the Portal:

```sh
sudo python3 -I -B system/install-helper.py --user "$USER"
```

This copies a fixed file list to `/usr/local/lib/odin2-portal-hardware/`, owned
by root, and enables only `odin2-portal-hardware.service`. The daemon validates
the exact board, CPU topology, governors, clock steps, fan and multicolor LEDs.
It accepts fixed operations over a Unix socket authenticated to the configured
desktop UID. No sudoers rule or writable sysfs permissions are added. Installing
or starting the helper does not change hardware settings.

Power/fan initialization and explicit controls acquire a session lease. Closing the popup
keeps settings active. Disabling the plugin, a shell restart, or loss of its
heartbeat restores the captured settings within 10 seconds. Suspend gaps also
release the lease. The running UI re-establishes saved power/fan choices after
resume, and a newly loaded plugin does so at login. Unrelated plugin rescans
retain this service and its lease through `keepLoaded:true`.
**Restore previous settings** releases all owned controls and suppresses automatic
initialization for the remainder of that service instance, including LED restoration.
A root-owned journal
recovers partial writes or a daemon restart on the same boot, and ignores stale
journals from an earlier boot. Writes are checked by reading back the kernel.
Detected external changes are preserved rather than overwritten.

Successful explicit power/fan changes are stored in the user's private
`~/.local/state/odin2-portal-hardware/power-fan.json` (or XDG state root).

LED choices are stored independently in private `lights.json` beside that file.
Each side remembers Manual/Follow theme, RGB channels, brightness and a separate
on/off choice. Lights off retains the last brightness for the next Apply. A
guarded upgrade seeds missing LED preferences from actual uniform ring
readback and selects Follow theme, preserving brightness and off state. When
adopting initially off rings, the unreadable previous intensity defaults to 50%
for the next Apply, while the rings remain off. Without
saved or adopted LED preferences, startup leaves LEDs alone until a choice is made.
Mixed groups are never flattened into a guessed state.

Follow theme matches the active palette to the existing red, green, blue, purple
and white choices. Light palettes and neutral accents, including Solitude, use
white. A matching stock theme's explicit `keyboard.rgb` takes precedence over
its accent: Tokyo Night's magenta maps to purple. Remaining colors use nearest
cyclic hue. This is an approximation, not calibrated color reproduction.
The service reads the current palette afresh at its existing sampling cadence
(normally three seconds while owned), including after theme-directory replacement.
Theme changes preserve saved brightness and keep off rings off. Apply color
selects Manual; in Follow theme, Apply brightness retains theme following.
Settings are saved only after matching successful readback. Steady state writes
nothing. Failed automatic synchronization reports an error and pauses until an
explicit control action or a new service instance; it does not blindly retry.
LED restoration waits for the existing owned power/fan session and uses the
unchanged off-first client/helper sequence. No root update or boot service is added.
Invalid saved data falls back to Saver/Auto without overwriting the bad file.
Startup waits for another owner's lease/recovery rather than stealing it.
No extra root operation is added; initialization uses the existing validated
fan and power requests. Root helper code and its thermal safeguards are unchanged.

The fan follows the hottest CPU/GPU sensor in Auto mode. At 85°C, missing CPU/GPU
sensors or sustained zero RPM, it uses full speed. Fan-off is excluded. Recovery
keeps full speed while temperatures are unavailable or at least 85°C, then
restores the original duty. Existing kernel thermal protection remains intact.
A kernel thermal binding or active LED trigger prevents competing ownership.
Physical fan/color, sustained load and resume acceptance remain separate checks.

Stop and remove the helper separately when retiring the plugin:

```sh
sudo systemctl disable --now odin2-portal-hardware.service
sudo rm /etc/systemd/system/odin2-portal-hardware.service
sudo rm -r /usr/local/lib/odin2-portal-hardware
sudo systemctl daemon-reload
```

Keep `/var/lib/odin2-portal-hardware/` until recovery is confirmed. If sensors are
hot or unavailable when the helper stops, its journal and full fan duty remain;
restart the helper to finish recovery once temperatures permit. Installer backups
are under that directory's `installations/` subdirectory.

## Terminal and IPC

```sh
./bin/odin2-portal-hardware
omarchy-shell odin2-portal-hardware status
omarchy-shell odin2-portal-hardware refresh
```

The terminal command emits one JSON snapshot. `--sys-root` accepts a synthetic
sysfs directory for offline tests and remains read-only. The IPC status reports
support, freshness, reader state and errors; it does not expose other plugins.

For actual QML state/layout JSON and safe panel navigation, see
[live inspection](docs/inspection.md). Inspection does not acquire hardware
control or open a popup by itself.

## Update and remove

Once published and installed through Omarchy's Git workflow, use its ordinary
update command and review the diff:

```sh
omarchy plugin update io.github.techluddite.odin2-portal-hardware
omarchy plugin disable io.github.techluddite.odin2-portal-hardware
omarchy plugin remove io.github.techluddite.odin2-portal-hardware
```

Removing the UI expires its lease; removing the helper is a separate step above.
The helper stores recovery state, not sensor history. Normal process logging is
managed by systemd and Quickshell.

## Development, CI and media

Follow [development and acceptance](docs/development.md),
[the architecture](docs/architecture.md), [preview-media provenance](docs/media/README.md)
and [the changelog](CHANGELOG.md).

CI follows the other Luddite plugins: unit/repository tests on pushes and PRs,
then pinned Luddite Scout and marketplace security-baseline scans on main
pushes. Actions have read-only repository permissions and immutable pins.
The installed-Omarchy QML fixture is a separate local check. Configured workflows
are not evidence of hosted CI success or marketplace verification.

Preview assets render actual plugin components with synthetic sensor values in
an isolated environment. They contain no personal windows or hardware capture
and do not establish physical acceptance. Runtime code is not restyled for them.
See the [light and dark theme examples](docs/media/README.md).

Report security issues privately as described in [SECURITY.md](SECURITY.md).
MIT; see [LICENSE](LICENSE) and [THIRD_PARTY.md](THIRD_PARTY.md).


### Inspect power levels

In Controls → Power, the original level buttons apply a level. The separate
**Inspect a level · no changes** selector previews Save, Balanced or Full without
sending a control request. It uses the command planner and advertised clock
steps to show CPU minimum/ceiling and governor behavior, plus the GPU ceiling.
Full requests the CPU ceiling through Performance; it does not write equal
minimum/maximum values. GPU governor/minimum, UFS governor/range, fan and RGB
remain unchanged by these presets. The **Observed now** readout shows actual
CPU/GPU/UFS governors and clocks, including choices made by another owner.
A hot reading at or above 85°C displays a warning and actual fan duty/RPM.
The preview is not a guarantee of effective clocks under thermal/QoS limits.
