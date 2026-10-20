import QtQuick
import QtQuick.Layouts
import qs.Commons as Theme
import qs.Ui as Ui

ColumnLayout {
  id: root
  property var service: null
  property color foreground: Theme.Color.popups.text
  property string section: "power"
  property string side: "both"
  property int fanPercent: 40
  property int brightness: 50
  property string colorName: "blue"
  property var colors: ({red: [255,0,0], green: [0,255,0], blue: [0,0,255], purple: [180,0,255], white: [255,255,255]})
  readonly property var state: service?.controls ?? ({available: false})
  readonly property bool ready: state.available === true && !state.occupied && !state.recovering && !service?.controlling
  spacing: Theme.Style.space(10)
  function send(request) { if (root.ready && root.service) root.service.control(request) }
  function lights(off) {
    var rgb = root.colors[root.colorName]
    root.send({op: "rgb", side: root.side, red: rgb[0], green: rgb[1], blue: rgb[2],
      brightness: off ? 0 : Math.round(root.brightness * 255 / 100)})
  }
  function ringSummary(prefix) {
    var first = root.state.rings?.[prefix + "1"]
    if (!first) return "—"
    for (var i = 2; i <= 4; i++) {
      var next = root.state.rings[prefix + i]
      if (!next || JSON.stringify(next) !== JSON.stringify(first)) return "Mixed groups"
    }
    if (first.brightness === 0) return "Off"
    var c = first.channels
    var hex = [c.red, c.green, c.blue].map(function(value) { return value.toString(16).padStart(2, "0") }).join("")
    return "#" + hex + " · " + Math.round(first.brightness / 255 * 100) + "%"
  }
  Ui.ButtonGroup {
    objectName: "controlTabs"
    foreground: root.foreground
    options: [{value: "power", label: "Power"}, {value: "fan", label: "Fan"}, {value: "lights", label: "Lights"}]
    value: root.section
    onChanged: function(value) { root.section = value }
  }
  Text {
    Layout.fillWidth: true
    text: root.service?.controlError || root.state.error || (root.state.occupied ? "Another panel controls this device." : "")
    visible: text !== ""
    textFormat: Text.PlainText
    wrapMode: Text.Wrap
    color: Theme.Color.urgent
    font.family: Theme.Style.font.family
    font.pixelSize: Theme.Style.font.caption
  }
  Text {
    Layout.fillWidth: true
    visible: !root.state.available
    text: "Monitoring is available. Install the separate Portal hardware helper to enable controls; see the README."
    textFormat: Text.PlainText
    wrapMode: Text.Wrap
    color: root.foreground
    font.family: Theme.Style.font.family
    font.pixelSize: Theme.Style.font.body
  }
  ColumnLayout {
    visible: root.section === "power"
    Layout.fillWidth: true
    spacing: Theme.Style.space(8)
    Ui.PanelSectionHeader { text: "LINUX PERFORMANCE LEVEL"; foreground: root.foreground }
    Ui.ButtonGroup {
      objectName: "powerPresets"
      enabled: root.ready
      foreground: root.foreground
      options: [{value: "saver", label: "Save"}, {value: "balanced", label: "Balanced"}, {value: "performance", label: "Full"}]
      value: root.state.power_mode || ""
      onChanged: function(value) { root.send({op: "power", mode: value}) }
    }
    Text {
      Layout.fillWidth: true
      text: "Save caps CPU and GPU clocks. Balanced allows CPU scaling with an 85% clock ceiling and the full GPU range. Full enables the CPU performance governor. These are Linux presets."
      textFormat: Text.PlainText
      wrapMode: Text.Wrap
      color: root.foreground
      font.family: Theme.Style.font.family
      font.pixelSize: Theme.Style.font.caption
    }
  }
  ColumnLayout {
    visible: root.section === "fan"
    Layout.fillWidth: true
    spacing: Theme.Style.space(8)
    Ui.PanelSectionHeader { text: "FAN CONTROL"; foreground: root.foreground }
    Ui.ButtonGroup {
      objectName: "fanModes"
      enabled: root.ready
      foreground: root.foreground
      options: [{value: "auto", label: "Auto"}, {value: "manual", label: "Manual"}, {value: "max", label: "Maximum"}]
      value: root.state.fan_mode || ""
      onChanged: function(value) { root.send({op: "fan", mode: value, percent: root.fanPercent}) }
    }
    StatRow { Layout.fillWidth: true; label: "Manual duty"; value: root.fanPercent + "%"; foreground: root.foreground }
    Ui.PanelSlider {
      objectName: "fanSlider"
      Layout.fillWidth: true
      enabled: root.ready
      minimum: 30; maximum: 100; integer: true; step: 5
      value: root.fanPercent
      onMoved: function(value) { root.fanPercent = Math.round(value) }
      onReleased: function(value) { root.send({op: "fan", mode: "manual", percent: Math.round(value)}) }
    }
    StatRow { Layout.fillWidth: true; label: "Actual duty"; value: (root.service?.snapshot?.fan?.duty_percent ?? "—") + "%"; foreground: root.foreground }
    StatRow { Layout.fillWidth: true; label: "Speed"; value: (root.service?.snapshot?.fan?.rpm ?? "—") + " RPM"; foreground: root.foreground }
    Text {
      Layout.fillWidth: true
      text: "Auto follows the hottest CPU or GPU reading. The minimum duty is 30%. High temperatures or missing sensors force full speed."
      textFormat: Text.PlainText
      wrapMode: Text.Wrap
      color: root.foreground
      font.family: Theme.Style.font.family
      font.pixelSize: Theme.Style.font.caption
    }
  }
  ColumnLayout {
    visible: root.section === "lights"
    Layout.fillWidth: true
    spacing: Theme.Style.space(8)
    Ui.PanelSectionHeader { text: "JOYSTICK RINGS"; foreground: root.foreground }
    Ui.ButtonGroup {
      foreground: root.foreground
      options: [{value: "both", label: "Both"}, {value: "left", label: "Left"}, {value: "right", label: "Right"}]
      value: root.side
      onChanged: function(value) { root.side = value }
    }
    Ui.ButtonGroup {
      objectName: "ringColors"
      foreground: root.foreground
      options: [{value: "red", label: "Red"}, {value: "green", label: "Green"}, {value: "blue", label: "Blue"}]
      value: root.colorName
      onChanged: function(value) { root.colorName = value }
    }
    Ui.ButtonGroup {
      foreground: root.foreground
      options: [{value: "purple", label: "Purple"}, {value: "white", label: "White"}]
      value: root.colorName
      onChanged: function(value) { root.colorName = value }
    }
    StatRow { Layout.fillWidth: true; label: "Brightness"; value: root.brightness + "%"; foreground: root.foreground }
    Ui.PanelSlider {
      objectName: "brightnessSlider"
      Layout.fillWidth: true
      minimum: 0; maximum: 100; integer: true; step: 5
      value: root.brightness
      onMoved: function(value) { root.brightness = Math.round(value) }
    }
    RowLayout {
      Layout.fillWidth: true
      Ui.Button { objectName: "applyLights"; text: "Apply color"; foreground: root.foreground; focusable: true; enabled: root.ready; onClicked: root.lights(false) }
      Ui.Button { text: "Lights off"; foreground: root.foreground; focusable: true; enabled: root.ready; onClicked: root.lights(true) }
    }
    StatRow { Layout.fillWidth: true; label: "Left applied"; value: root.ringSummary("l"); foreground: root.foreground }
    StatRow { Layout.fillWidth: true; label: "Right applied"; value: root.ringSummary("r"); foreground: root.foreground }
  }
  Ui.PanelSeparator { Layout.fillWidth: true; foreground: root.foreground }
  Ui.Button {
    objectName: "restoreHardware"
    text: "Restore previous settings"
    foreground: root.foreground
    focusable: true
    enabled: root.state.available && !root.state.occupied && !root.service?.controlling
    onClicked: if (root.service) root.service.control({op: "restore"})
  }
  Text {
    Layout.fillWidth: true
    text: "Changes last while this plugin is running. Closing the popup keeps them active. Disabling the plugin or restarting the shell restores the previous settings within 10 seconds."
    textFormat: Text.PlainText
    wrapMode: Text.Wrap
    color: root.foreground
    font.family: Theme.Style.font.family
    font.pixelSize: Theme.Style.font.caption
  }
}
