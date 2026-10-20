# Live QML inspection

The panel exposes JSON inspection through Omarchy's existing local IPC. This
inspects the actual Qt Quick tree, not an HTML reconstruction. It reads only
this hardware popup's visual subtree. No desktop capture, other-window
inspection, report/draft access or additional listener is involved.

```sh
omarchy-shell odin2-portal-hardware inspect
omarchy-shell odin2-portal-hardware navigate '{"op":"open"}'
omarchy-shell odin2-portal-hardware navigate '{"op":"section","value":"fan"}'
omarchy-shell odin2-portal-hardware inspect
omarchy-shell odin2-portal-hardware navigate '{"op":"close"}'
```

Inspection includes open/tab/section state, viewport and scroll geometry, helper
status, stale/error flags, and at most 256 visual nodes to depth 12. Nodes include
object names, type, parent path, viewport-relative bounds, visibility, clipping
intersection, enabled/focus state and bounded text/value. Hidden subtrees are
omitted; `in_view` accounts for clipping and opacity. Closed popups and truncation
are explicit. This is layout/state evidence, not proof of rendered pixels,
physical input, fan operation or RGB color.

Navigation permits only `open`, `close`, `tab`, `section` and clamped `scroll`.
Tab values are overview/controls/clocks/sensors; sections are power/fan/lights.
There is no eval, arbitrary method/click or hardware-write operation here.
Hardware control remains a separate explicit endpoint. Reading inspection alone
does not open/focus a popup or acquire a hardware lease.

The Portal project's `scripts/portal-panel.py` adds a terminal watch over one
existing SSH connection, with JSON Lines or readable text/geometry. It can also
watch the existing agent status endpoint, which provides metadata rather than a
full visual tree. Existing SSH identity verification remains in force. No
screenshot stream, browser or websocket service is needed.

`Scene.js` is independent of hardware control and can be adapted to another
explicitly selected QML root. The isolated QML fixture exercises real scene
inspection, hidden-section exclusion and safe navigation on offscreen and
private Wayland surfaces.
