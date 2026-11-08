# Development and acceptance

Created October 20, 2026 as a separate local repository after the user selected
**Odin2 Portal Hardware**. Identity:
`io.github.techluddite.odin2-portal-hardware`. Remote publication, installation
and physical control acceptance are separate from this source work.

## Local checks

```sh
python3 -B -m unittest discover -s tests -v
omarchy plugin validate .
python3 -B tests/qml_smoke.py
python3 -B tests/qml_smoke.py --theme hackerman --artifacts previews/hackerman
python3 -B tests/qml_smoke.py --theme catppuccin-latte --artifacts previews/latte
python3 -B tests/qml_smoke.py --theme gruvbox --artifacts previews/gruvbox
```

The Python suite uses disposable sysfs trees. It covers exact model gating,
CPU/GPU/battery units, hottest-sensor selection, zero/missing/invalid values,
ambiguous fan discovery, bounded attribute reads and the actual CLI. It never
opens a live input, audio or hardware-control interface.

The QML fixture runs the actual reader against synthetic sysfs and renders the
real plugin with installed Commons/Ui. Temporary HOME/config/state/cache/data/
runtime directories and an unavailable session bus isolate it from the desktop.
Offscreen mode replaces only KeyboardPanel's layer-shell wrapper. The optional
`--wayland-socket /absolute/private/socket` uses the actual KeyboardPanel on a
separately started private headless compositor; never pass the desktop socket.
The compositor must use headless outputs and no DRM/libinput backend.

Checks cover real reader integration, correct units, popup polling ownership,
all three tabs, narrow width, zero readings, stale/recovery behavior, live theme
bindings and unsupported-device behavior. Artifacts are synthetic UI renders.
They are not live hardware screenshots or physical touch/controller acceptance.

## CI conventions

Reviewed the user's five currently listed plugin repositories; exact pins are
in [repository-conventions.json](repository-conventions.json). The workflow
follows Jeans Instability's three-job pattern: unit/repository tests on pushes
and PRs, pinned Luddite Scout on main pushes, and the pinned marketplace scanner.
All findings and unexpected capabilities fail. No capability exception was added
for the initial read-only version. The 0.2.0
helper adds explicit privilege/service capabilities requiring separate review;
the strict CI gates remain in place. Scanner pins match the
reviewed repos and are not claims about the newest scanner releases.

Hosted checks require a published repository. Local tests do not establish a
successful GitHub Actions run or marketplace verification.

## Remaining acceptance

- Physical touch/focus, theme/font/display scaling and suspend/resume behavior.
- Sustained polling overhead and real sensor accuracy/availability.
- Physical acceptance for each fan, power and RGB operation; software readback
  alone does not establish fan acoustics, actual color or sustained behavior.
- Publication/hosted CI and marketplace submission when requested.

Initial development caught a QML property collision with Item.data, a row-layout
feedback loop, missing fake-bar tooltip properties and screenshot callbacks that
captured the following tab. These were corrected in the fixture/source; they
were not live Portal desktop failures. Record final check counts and native
results in the parent Portal integration handoff.

## October 20 initial monitoring acceptance

- 27 unit/repository checks pass on both host and native aarch64 Portal.
- Manifest validation passes on both machines.
- Real-reader/synthetic-sysfs QML fixture passes host offscreen, native ARM
  offscreen and a private headless Sway Wayland instance with the real popup.
  No QML binding-loop, type, reference or layout-recursion warnings remain.
- Hackerman, Catppuccin Latte and Gruvbox previews pass. Nine themed images and
  a root preview are reviewed exports, with hashes in the media manifest.
- A single native read-only snapshot discovers three CPU policies, one GPU,
  the fan/battery and 41 thermal sensors. No hardware setting is written.

This validates initial source/discovery/rendering. The plugin is not installed
or published; no hosted CI, physical UI/control, sustained overhead or suspend
acceptance is claimed. Later hardware-writing increments remain unimplemented.

## October 20 local Portal test installation

The user subsequently requests installation for testing. The reviewed 36-file
source/media snapshot is installed in the user plugin directory, enabled in
the right bar section through Omarchy's supported discovery/enable commands,
and opened through the shell's summon command. No shell restart was required.

Live readback reports supported/sampled, no stale data or reader error, and
read-only access with hardware controls unavailable. The bar icon is visible
and the popup layer is mapped. Existing shell preferences compare equal after
removing only the new plugin entry; protected config hashes, the controller's
14 bindings/OS mode/Portal profile and overlay view are preserved.

Before/after shell configuration, preservation hashes and installed-source
manifest are banked privately at:

`~/.local/state/odin2-portal-hardware/deployments/20261020T102859294202Z`

Disable with `omarchy plugin disable io.github.techluddite.odin2-portal-hardware`;
remove with the ordinary plugin removal command when wanted. Use the saved shell
copy only after reviewing newer user changes. The backend has no hardware policy
to restore. The installed source is the frozen pre-installation build; these
subsequent documentation updates do not change runtime code.

This supersedes the earlier not-installed status. The user's physical popup,
touch/focus and sustained/resume observations are still pending. No hardware
controls, packages, boot, recording, source commit or publication were changed.

## 0.2.0 control increment

The source now adds fan, Linux CPU/GPU presets and joystick rings. The separate
helper installer requires explicit root execution and validates the Portal before
enabling its own unit. Monitoring remains independently usable. Engine fixtures
exercise partial-write recovery, lease loss, suspend gaps, same/new-boot recovery,
channel ordering, external writers, invalid requests and sensor faults. QML
fixtures use a synthetic control responder, never the live helper socket.
Native tests and actual-device acceptance are recorded in the Portal project;
the earlier 0.1.0 paragraphs above are historical evidence.

## Local control deployment and inspection

The 0.2.0 control build was installed and healthy on the Portal. Its fresh local
source directory ends in `.local-0.2.0`: an update at the previous URL reused
cached QML, so deployment rolled back and then used a fresh source URL. No
packaged shell edit or full shell restart was needed. Plugin identity remains
`io.github.techluddite.odin2-portal-hardware`; Omarchy discovers identity from
the manifest. Preserve this distinction in local update/remove/recovery tools.

The subsequent local 0.2.1 build adds [actual QML inspection](inspection.md), with
fixture tests for bounded scene traversal and explicit navigation. This uses
existing IPC and SSH; it adds no root operation or listener. The Portal project
records exact installed paths, source hashes, backups and current acceptance.

## October 20 local commit checkpoint

Version 0.2.1 is installed/enabled in the right bar at
`~/.config/omarchy/plugins/io.github.techluddite.odin2-portal-hardware.local-0.2.1/`.
The separately installed root helper is active/enabled. All 54 installed source
files match the frozen deployment receipt in the Portal project; this later
development-document update is the only source difference for the local commit.
Runtime code, manifest and reviewed media remain byte-for-byte identical.

54 host and 54 native ARM checks, host/native manifests and real-Ui QML checks
pass. Native probes verify presets/fan/RGB writes, readback, restoration and
abandoned-lease recovery. Live QML inspection and user selections are observed;
closed-popup heartbeats retain those choices. The user is testing the panel.
Preserve newer hardware/UI preferences and do not infer physical acceptance.
See the Portal project's `docs/odin2-portal-hardware-controls-20261020.md` and
`docs/portal-overlay-bridge-20261020.md` for recovery and acceptance records.

The user authorizes a local-only source commit if checks and the exact-index
privacy/media audits pass. No remote, hosted CI, marketplace verification,
publication or new runtime deployment is part of this checkpoint.

## October 21 LED persistence and theme follow-up

Local 0.4.0 adds per-side LED preferences, theme matching and explicit Manual /
Follow theme controls. Isolated engine fixtures cover off-state/theme/brightness
preservation, restart restoration, failed/unowned writes, mixed groups, adoption,
invalid input and complete palette replacement. `tests/lighting_qml.py` exercises
real Service process synchronization, failure latching and explicit recovery;
the existing controls smoke fixture covers the new buttons and saved brightness.
The parent Portal repository records native validation, deployment and remaining
physical appearance/startup/resume acceptance. No root helper source change is
required; retain its original installed hashes.

## October 21 local 0.3.3 checkpoint

The user requests documentation and a local-only commit after testing. The
installed plugin is 0.3.3. The parent Portal repository records deployment,
recovery and acceptance in its October 21 handoff and dedicated startup,
preset-detail, theme and LED-brightness records.

The source now retains the service across registry rescans, starts with saved
validated power/fan preferences or Saver/Auto, and supports guarded same-boot
session adoption without adding a root API. Preset descriptions use the same
pure plan as CPU writes; popup controls explicitly inherit popup text colors.
RGB changes validate the complete request, confirm an off transaction for the
selected groups, then apply the target. The two RGB operations are individually
journaled and can briefly blink; failure is reported without blind retry.
The deployed root helper remains the reviewed 0.2.1 installation.

76 disposable-tree unit/repository checks pass on host and native ARM. Startup
QML, manifest validation, dark adaptive-bar and light popup fixtures pass.
Native/installed LED probes and their restoration are recorded by the parent;
they are not repeated for this checkpoint. No new physical LED, sustained
thermal, suspend or startup acceptance is inferred. Hosted CI/publication remain
pending. The user's later Saver/Auto and white half-brightness choices supersede
the earlier Full/Max/green probe restoration.

This section is a source documentation update only. The installed 58-file
receipt remains frozen; do not redeploy solely to synchronize this paragraph.

## 0.4.1 and 0.4.2: kernel-owned fan (2026-11-07)

The Portal moved to mainline Linux 7.4-rc1, whose device tree binds the fan to
thermal zone `cpu7-bottom-thermal` (step_wise, active trips 50 to 85 °C). The
helper detects a `pwm-fan` cooling device linked from any thermal zone and
reports `fan_owner: kernel` in its status. Startup then restores the power
level alone and keeps the saved fan choice on disk for kernels where the helper
owns the fan again. The Fan tab shows the kernel control and disables its
modes.

0.4.1 fixed this in `backend/preferences.py` but missed the same readiness
check in `Service.qml`, so startup reran on every refresh, the controls stayed
busy and power buttons needed a second press. 0.4.2 fixes the QML check and
hardens `tests/startup_qml.py` to require readiness to hold for 1.5 s; it fails
against 0.4.1's `Service.qml`. 0.4.2 also removes the refresh button, moves the
remembered-settings note to the README and shows the power levels as a table
of CPU, GPU and UFS ceilings.

91 unit tests and the hardware, startup and lighting QML suites pass on the
Portal. The root helper was reinstalled for `fan_owner` (installer backup
`/var/lib/odin2-portal-hardware/installations/20261107T225708Z`). Operator
confirmed single-press power levels on 0.4.2.

Open:

- Manual fan control when the kernel owns the fan. Candidate: set the owning
  thermal zone's `mode` to `disabled` while Manual or Max is active, drive
  `pwm1` from the helper, and re-enable the zone on release, suspend, helper
  exit and above the hot limit. Tracked as backlog H8 in the Portal project.
- Published 2026-11-07 as `TechLuddite/odin2-portal-hardware`. Hosted CI:
  tests pass. Luddite Scout fails on S7 high "uses sudo" for
  `system/install-helper.py` (the root helper is by design) and on S7 medium
  "collects a child process's whole output before checking its size" at
  `Service.qml:104` (the handoff process; worth bounding). The marketplace
  baseline also fails; marketplace submission is not planned yet, so that is
  accepted for now.
- With a kernel-owned fan the Fan tab still shows the disabled mode buttons,
  slider and the Auto explanation under the kernel note. Hiding them in that
  state would read more clearly.
- README screenshots are live captures from 2026-11-07 (see docs/media).
