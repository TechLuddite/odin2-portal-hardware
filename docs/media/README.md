# Preview media

`preview.png` at the repository root and the images here are screenshots of the
plugin running on the maintainer's AYN Odin 2 Portal, taken 2026-11-07 with
`grim` on mainline Linux 7.4-rc1, Omarchy's Tokyo Night theme and plugin 0.4.2.
The readings are live values from that device at capture time.

The panel was opened and switched between views with the plugin's QML bridge,
with no touch input. Each capture is cropped to the popup border, so no
wallpaper, other window or desktop content is included. The Clocks and Sensors
views are taller than the screen and scroll, so their images show the top of
the view.

| View | Image |
| --- | --- |
| Overview | [overview.png](overview.png) |
| Details, Clocks | [details-clocks.png](details-clocks.png) |
| Details, Sensors | [details-sensors.png](details-sensors.png) |
| Controls, Power | [controls-power.png](controls-power.png) |
| Controls, Fan | [controls-fan.png](controls-fan.png) |
| Controls, Lights | [controls-lights.png](controls-lights.png) |

On mainline Linux a kernel thermal zone drives the fan, so the Fan view shows
the kernel-control note with the fan modes disabled. Hashes and dimensions are
in [assets.json](assets.json). Earlier synthetic renders in three themes were
replaced by these captures and remain in the Git history.
