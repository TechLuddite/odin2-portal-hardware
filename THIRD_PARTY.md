# Credits and provenance

## Runtime and device interfaces

- **Omarchy — David Heinemeier Hansson and contributors:** MIT shell and
  Commons/Ui component APIs. The plugin imports the installed UI kit rather
  than bundling it. See [omacom/omarchy](https://github.com/omacom/omarchy).
- **Quickshell and Qt contributors:** the installed QML host, process and
  window APIs; no framework sources or binaries are redistributed here.
- **Linux kernel and board-support contributors:** Qualcomm CPUFreq/devfreq,
  thermal, pwm-fan and battery interfaces used by the Portal adapters.
  Board integration and its credit chain are recorded in the
  [Portal project](https://github.com/TechLuddite/omarchy-mobile-odin2).

- **Teguh Sobirin and Pocknix board-support contributors:** Portal device-tree
  definitions identify the pwm-fan and eight multicolor LED groups. Hardware
  layout research used `qcs8550-ayn-odin2portal.dts` and the shared AYN board
  definition; no driver/device-tree source is bundled or copied here.
- Linux's primary interface documentation informed the original control engine:
  [multicolor LEDs](https://docs.kernel.org/leds/leds-class-multicolor.html),
  [pwm-fan](https://docs.kernel.org/hwmon/pwm-fan.html) and
  [CPUFreq](https://docs.kernel.org/admin-guide/pm/cpufreq.html).

## Design research, without copied implementation

- **MaSi/SteamOS-Ubuntu, Basit and contributors; Hooandee/Panel de Control;
  Decky Loader:** SM8550-Power's profile/fan/monitor organization was the
  starting design reference. Reviewed Basit's source at
  `4673fa6bfc8b6a598ef799ed0e88f98a9b045285`. That power component is
  GPL-3.0-or-later; none of its code or assets is included in this MIT plugin.
- **Steve McQueen / Thermals & Fans:** native Omarchy curve/profile panel and
  backend-separation research.
- **LukasMoriarty / Apple Silicon Thermals:** existing ARM-oriented panel
  research; its Apple SMC backend is not used for the Qualcomm Portal.
- **Centro, Fan & Thermal Control, Aeolus and PowerKit authors:** comparative
  capability and hardware-specificity research, recorded in the Portal project.

## Repository conventions

The user's published Luddite Gestures, PXE Dust, Jeans Instability, Luddite Scout
and Luddite Voice OSD were inspected for documentation, pinned CI/security jobs
and media conventions. CI is adapted from TechLuddite's MIT Jeans Instability
workflow; the runtime implementation is original to this repository. Exact
reviewed repositories, commits and file hashes are in
[repository-conventions.json](docs/repository-conventions.json).

Preview media use actual installed Omarchy components and theme tokens with
synthetic sensor readings. Original theme files and wallpapers are not bundled
as separate assets; see [media details](docs/media/README.md).
