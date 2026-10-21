#!/usr/bin/env python3
"""Render real Omarchy components against synthetic sysfs, outside the desktop.

Offscreen replaces only the layer-shell wrapper. --wayland-socket must refer to
a private headless compositor; it exercises the actual KeyboardPanel as well.
Neither mode installs the plugin, reads live sysfs or injects hardware input.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from fixture import tree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shell-dir", type=Path, default=Path("/usr/share/omarchy/shell"))
    parser.add_argument("--wayland-socket", type=Path)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--theme", choices=["hackerman", "catppuccin-latte", "gruvbox", "osaka-jade"])
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    if args.artifacts:
        args.artifacts = args.artifacts.resolve()
        args.artifacts.mkdir(parents=True, exist_ok=True)
    if args.wayland_socket:
        assert args.wayland_socket.is_absolute() and args.wayland_socket.is_socket()
    with tempfile.TemporaryDirectory(prefix="portal-hardware-qml-") as temp:
        root = Path(temp)
        for folder in ["home", "runtime", "config", "state", "cache", "data"]:
            (root / folder).mkdir(mode=0o700)
        for path in repo.glob("*.qml"):
            shutil.copy2(path, root / path.name)
        for path in repo.glob("*.js"):
            shutil.copy2(path, root / path.name)
        shutil.copytree(repo / "backend", root / "backend", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(repo / "bin", root / "bin")
        (root / "Commons").symlink_to(args.shell_dir.resolve() / "Commons", target_is_directory=True)
        shutil.copytree(args.shell_dir / "Ui", root / "Ui")
        if not args.wayland_socket:
            (root / "Ui/KeyboardPanel.qml").write_text('''import QtQuick
Item {
  property var anchorItem: null
  property var owner: null
  property var bar: null
  property bool open: false
  property var focusTarget: null
  property real contentWidth: 480
  property real contentHeight: 600
  width: contentWidth; height: contentHeight
  visible: open
  function fittedContentWidth(v) { return v }
  function fittedContentHeight(v) { return Math.min(600, v) }
  onOpenChanged: {
    if (bar && open) bar.requestPopout(owner)
    else if (bar) bar.releasePopout(owner)
  }
}
''')
        if args.theme:
            theme = args.shell_dir.parent / "themes" / args.theme
            dest = root / "home/.local/state/omarchy/current/theme"
            dest.mkdir(parents=True)
            for name in ["colors.toml", "shell.toml"]:
                if (theme / name).exists():
                    shutil.copy2(theme / name, dest / name)
        sysroot = tree(root / "sys")
        fake_control = root / "fake-control.py"
        fake_control.write_text('''import json, sys
request = json.loads(sys.argv[-1])
assert request["op"] in {"power", "fan", "rgb", "restore"}
print(json.dumps({"available": True, "owned": request["op"] != "restore", "error": "", "power_mode": request.get("mode")}))
''')
        command = ["/usr/bin/python3", "-I", "-B", str(root / "bin/odin2-portal-hardware"), "--sys-root", str(sysroot)]
        qml = '''import QtQuick
import Quickshell
import qs.Commons as Theme
import qs.Ui as Ui
ShellRoot {
  id: root
  property int stage: 0
  property int attempts: 0
  property var good: null
  property var savedForeground: null
  property var savedShellValues: null
  function check(value, message) { if (!value) throw new Error(message) }
  function enableControls() {
    service.snapshot = Object.assign({}, service.snapshot, {controls: {available: true, owned: true, rings: {}}})
  }
  function find(item, name) {
    if (item.objectName === name) return item
    for (var child of item.children || []) { var hit = find(child, name); if (hit) return hit }
    return null
  }
  function capture(name, nextStage, after) {
    root.stage = -1
    if (__ARTIFACTS__ !== "") card.grabToImage(function(result) {
      if (!result.saveToFile(__ARTIFACTS__ + "/" + name + ".png")) Qt.exit(1)
      if (after) after()
      root.stage = nextStage
    })
    else { if (after) after(); root.stage = nextStage }
  }
  Service { id: service; startupManaged: false; readerCommand: __COMMAND__; controlCommand: __CONTROL__ }
  QtObject {
    id: bar
    property bool vertical: false
    property bool foregroundAnimationEnabled: false
    property string position: "top"
    property int barSize: 30
    property color barForeground: "#090f0d"
    property color foreground: Theme.Color.popups.text
    property color background: Theme.Color.popups.background
    property color urgent: Theme.Color.urgent
    property string fontFamily: Theme.Style.font.family
    property var activePopout: null
    property QtObject shell: QtObject { function serviceFor(name) { return service } }
    function requestPopout(owner) { activePopout = owner }
    function releasePopout(owner) { if (activePopout === owner) activePopout = null }
    function showTooltip(owner, text) {}
    function hideTooltip(owner) {}
  }
  FloatingWindow {
    id: window
    visible: true
    implicitWidth: 540
    implicitHeight: 700
    color: Theme.Color.popups.background
    Ui.BorderSurface {
      id: card
      x: 24; y: 24
      width: monitor.width + contentLeftInset + contentRightInset
      height: monitor.implicitHeight + contentTopInset + contentBottomInset
      padding: Theme.Style.space(14)
      color: Theme.Color.popups.background
      radius: Theme.Style.cornerRadius
      borderSpec: Theme.Border.surfaceSpec("popups", "border", Theme.Color.popups.border, Math.max(1, Theme.Style.space(2)))
      MonitorContent {
        id: monitor
        width: Math.min(Theme.Style.space(460), window.width - 80)
        x: card.contentLeftInset; y: card.contentTopInset
        service: service
      }
    }
    BarWidget { id: widget; bar: bar; width: 30; height: 30 }
  }
  Timer {
    interval: 100; running: true; repeat: true
    onTriggered: {
      try {
        if (++root.attempts > 100) throw new Error("fixture timeout at stage " + root.stage)
        if (root.stage < 0) return
        if (root.stage === 0) {
          if (!service.snapshot || service.busy) return
          root.check(service.supported && !service.stale, "real reader supported")
          root.check(service.snapshot.thermals.cpu_c === 95.5, "hottest sensor")
          root.good = service.snapshot
          root.savedForeground = Theme.Color.foreground
          root.savedShellValues = Theme.Color.shellValues
          widget.open()
          root.stage++
        } else if (root.stage === 1) {
          root.check(widget.opened && service.readers.length === 1, "popup requests fast readings")
          root.check(widget.panel.form.foreground.toString() === Theme.Color.popups.text.toString(), "popup text uses popup palette when transparent bar text differs")
          widget.close()
          root.check(!widget.opened && service.readers.length === 0, "popup releases fast readings")
          root.check(root.find(monitor, "fanRpm").value === "2400 RPM", "real fan readout")
          root.capture("overview", 2, function() { monitor.currentTab = "clocks" })
        } else if (root.stage === 2) {
          root.check(root.find(monitor, "gpuClock").value === "680 MHz", "GPU units")
          root.capture("clocks", 3, function() { monitor.currentTab = "sensors" })
        } else if (root.stage === 3) {
          root.capture("sensors", 4, function() { monitor.currentTab = "overview"; monitor.width = 300 })
        } else if (root.stage === 4) {
          root.check(root.find(monitor, "monitorTabs").width <= monitor.width, "narrow tabs fit")
          var updated = JSON.parse(JSON.stringify(root.good))
          updated.fan.rpm = 0; updated.battery.capacity_percent = 0
          root.capture("narrow", 5, function() { service.accept(JSON.stringify(updated)) })
        } else if (root.stage === 5) {
          root.check(root.find(monitor, "fanRpm").value === "0 RPM", "zero RPM stays zero")
          root.check(root.find(monitor, "batteryCharge").value === "0%", "zero charge stays zero")
          service.accept("broken-json")
          root.check(service.stale && service.snapshot.battery.capacity_percent === 0, "failed read retains stale values")
          root.capture("unavailable", 6, function() {
            service.accept(JSON.stringify(root.good))
            root.check(!service.stale, "valid sample recovers")
            Theme.Color.foreground = "#123456"
            Theme.Color.shellValues = {}
          })
        } else if (root.stage === 6) {
          root.check(monitor.foreground.toString() === "#123456", "live theme binding")
          root.check(widget.panel.form.foreground.toString() === "#123456", "real popup follows live theme changes independently of bar")
          Theme.Color.shellValues = {"popups.text": "#e8c070", "bar.text": "#090f0d"}
          root.check(widget.panel.form.foreground.toString() === "#e8c070", "popup surface override wins over global and bar text")
          var unknown = JSON.parse(JSON.stringify(root.good))
          unknown.supported = false; unknown.reason = "This plugin currently supports the AYN Odin 2 Portal."
          service.accept(JSON.stringify(unknown))
          root.stage++
        } else if (root.stage === 7) {
          root.check(!root.find(monitor, "monitorTabs").visible, "unsupported device has no monitor tabs")
          root.capture("unsupported", 8)
        } else if (root.stage === 8) {
          Theme.Color.foreground = root.savedForeground
          Theme.Color.shellValues = root.savedShellValues
          var controlled = JSON.parse(JSON.stringify(root.good))
          controlled.controls = {available: true, owned: false, rings: {}}
          service.accept(JSON.stringify(controlled))
          monitor.width = 460
          monitor.currentTab = "controls"
          root.stage++
        } else if (root.stage === 9) {
          root.check(root.find(monitor, "powerPresets").enabled, "helper enables power presets")
          var originalRequest = service.requestPayload
          root.find(monitor, "presetPreview").changed("saver")
          root.check(service.requestPayload === originalRequest, "preview never dispatches controls")
          root.check(root.find(monitor, "presetDetails").text.indexOf("Minimum equals maximum: fixed range.") !== -1, "Save detects a fixed range when advertised steps require it")
          root.find(monitor, "presetPreview").changed("performance")
          root.check(root.find(monitor, "presetDetails").text.indexOf("minimum is not pinned") !== -1, "Full describes request versus pin")
          root.check(root.find(monitor, "presetDetails").text.indexOf("Governor unchanged") !== -1, "GPU unchanged fields explicit")
          root.check(root.find(monitor, "liveGovernors").text.indexOf("UFS: Performance · 300 MHz") !== -1, "trial governor visible separately")
          root.check(root.find(monitor, "thermalWarning").visible, "hot CPU warning visible")
          root.find(monitor, "powerPresets").changed("saver")
          root.check(JSON.parse(service.requestPayload).op === "power", "power command")
          root.capture("controls-power", 10, function() { root.find(monitor, "hardwareControls").section = "fan" })
        } else if (root.stage === 10) {
          if (service.controlling) return
          root.enableControls()
          root.find(monitor, "fanModes").changed("manual")
          root.check(JSON.parse(service.requestPayload).percent === 40, "fan command percent")
          root.capture("controls-fan", 11, function() { root.find(monitor, "hardwareControls").section = "lights" })
        } else if (root.stage === 11) {
          if (service.controlling) return
          root.enableControls()
          root.find(monitor, "applyLights").clicked()
          root.check(JSON.parse(service.requestPayload).blue === 255, "RGB command")
          root.capture("controls-lights", 12, function() { monitor.width = 300 })
        } else if (root.stage === 12) {
          if (service.controlling) return
          root.enableControls()
          root.check(root.find(monitor, "ringColors").width <= monitor.width, "narrow color buttons fit")
          root.find(monitor, "restoreHardware").clicked()
          root.check(JSON.parse(service.requestPayload).op === "restore", "restore command")
          root.capture("controls-narrow", 13)
        } else if (root.stage === 13) {
          root.check(widget.panel.navigate({op: "section", value: "fan"}).ok, "semantic navigation")
          root.check(widget.panel.form.currentTab === "controls", "navigation selects controls")
          root.check(widget.panel.navigate({op: "eval", value: "Qt.quit()"}).error, "no evaluation operation")
          root.check(widget.panel.navigate({op: "section", value: "fan", command: "true"}).error, "unknown field rejected")
          root.check(widget.panel.navigate({op: "scroll", value: -999}).ok, "bounded scroll action")
          root.check(widget.panel.inspect().scroll.y === 0, "scroll clamps to zero")
          root.check(widget.panel.navigate({op: "open"}).ok, "bridge opens its own popup")
          root.stage++
        } else if (root.stage === 14) {
          root.check(widget.panel.inspect().scene.nodes.length > 10, "real QML scene inspection")
          root.check(widget.panel.inspect().scene.nodes.length <= 256, "bounded QML scene")
          root.check(widget.panel.inspect().scene.nodes.some(function(node) { return node.name === "fanSlider" }), "fan slider in live scene")
          root.check(!widget.panel.inspect().scene.nodes.some(function(node) { return node.name === "ringColors" }), "hidden section excluded")
          root.check(widget.panel.navigate({op: "close"}).ok, "bridge closes its own popup")
          root.stage++
        } else {
          console.log("PORTAL HARDWARE QML PASS")
          Qt.quit()
        }
      } catch (error) { console.error(error); Qt.exit(1) }
    }
  }
}
'''.replace("__COMMAND__", json.dumps(command)).replace("__CONTROL__", json.dumps(["/usr/bin/python3", "-I", "-B", str(fake_control)])).replace("__ARTIFACTS__", json.dumps(str(args.artifacts) if args.artifacts else ""))
        (root / "shell.qml").write_text(qml)
        env = {**os.environ, "HOME": str(root / "home"), "XDG_RUNTIME_DIR": str(root / "runtime"),
               "XDG_CONFIG_HOME": str(root / "config"), "XDG_STATE_HOME": str(root / "state"),
               "XDG_CACHE_HOME": str(root / "cache"), "XDG_DATA_HOME": str(root / "data"),
               "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent", "QT_QPA_PLATFORM": "offscreen",
               "QT_QPA_PLATFORMTHEME": "", "QT_QUICK_CONTROLS_STYLE": "Basic",
               "QT_QUICK_BACKEND": "software", "LANG": "C.UTF-8"}
        for name in ["DISPLAY", "WAYLAND_DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE", "SWAYSOCK", "QS_CONFIG_PATH", "QS_CONFIG_NAME"]:
            env.pop(name, None)
        if args.wayland_socket:
            env.update(QT_QPA_PLATFORM="wayland", WAYLAND_DISPLAY=str(args.wayland_socket))
        proc = subprocess.run(["quickshell", "--no-color", "-p", str(root / "shell.qml")],
                              env=env, text=True, capture_output=True, timeout=20)
        output = proc.stdout + proc.stderr
        print(output, end="")
        forbidden = ["Binding loop", "recursive rearrange", "TypeError:", "ReferenceError:",
                     "Unable to assign", "Failed to load", "ERROR:"]
        if proc.returncode or "PORTAL HARDWARE QML PASS" not in output or any(s in output for s in forbidden):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
