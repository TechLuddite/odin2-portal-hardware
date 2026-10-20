# Preview media

Media follow the other Luddite plugins: `preview.png` at the repository root,
additional themed views here, and a clear distinction between demonstration
data and physical acceptance. Root/public media must show the actual plugin UI.

The fixture renders `MonitorContent.qml` with Omarchy's installed Commons/Ui
components in a matching `Ui.BorderSurface`, using the same popup border,
padding and theme tokens as the panel. Sensor readings are scripted sysfs data.
No live desktop, personal windows, accounts or device screenshots are captured.
The runtime UI is not separately restyled for these images.

The source fixture is [tests/qml_smoke.py](../../tests/qml_smoke.py); commands are
in [development.md](../development.md). `--theme` copies installed Hackerman,
Catppuccin Latte or Gruvbox color/shell tokens into the temporary HOME. Original
theme files and wallpapers are not redistributed separately. The images depict
an isolated component render, not a claim that the plugin is installed or that
hardware controls work.

Scratch images and capture logs belong in ignored `previews/` or `private/`.
Only deliberately reviewed images should move into this directory or become
the root preview. A demo GIF/video can be added when actual controls exist;
do not depict unimplemented controls with fabricated interaction.

## Reviewed images — October 20

| Theme | Overview | Clocks | Sensors |
| --- | --- | --- | --- |
| Hackerman | [Overview](hackerman-overview.png) | [Clocks](hackerman-clocks.png) | [Sensors](hackerman-sensors.png) |
| Catppuccin Latte | [Overview](catppuccin-latte-overview.png) | [Clocks](catppuccin-latte-clocks.png) | [Sensors](catppuccin-latte-sensors.png) |
| Gruvbox | [Overview](gruvbox-overview.png) | [Clocks](gruvbox-clocks.png) | [Sensors](gruvbox-sensors.png) |

The [root preview](../../preview.png) comes from the private headless Wayland
fixture. Other images use the same components in the offscreen fixture.
[Asset hashes/dimensions](assets.json) distinguish the reviewed exports from
scratch images. The hot CPU value is a deliberate test of hottest-sensor
selection, not a recorded temperature or an accepted fan policy.

## Controls — 0.2.0

| Theme | Power | Fan | Lights |
| --- | --- | --- | --- |
| Hackerman | [Power](hackerman-controls-power.png) | [Fan](hackerman-controls-fan.png) | [Lights](hackerman-controls-lights.png) |
| Catppuccin Latte | [Power](catppuccin-latte-controls-power.png) | [Fan](catppuccin-latte-controls-fan.png) | [Lights](catppuccin-latte-controls-lights.png) |
| Gruvbox | [Power](gruvbox-controls-power.png) | [Fan](gruvbox-controls-fan.png) | [Lights](gruvbox-controls-lights.png) |

Control views use the real UI with a synthetic helper responder. They demonstrate
layout and theme behavior, not live fan/color acceptance. The root image and named themed exports show the current UI; the root overview
comes from the private headless Wayland fixture.
