import QtQuick
import QtQuick.Layouts
import qs.Commons as Theme
import qs.Ui as Ui
import "Model.js" as Model

FocusScope {
  id: root
  property var service: null
  property color foreground: Theme.Color.popups.text
  property string currentTab: "overview"
  readonly property var readings: service?.snapshot ?? null
  readonly property bool supported: readings?.supported === true
  readonly property var controlsView: hardwareControls
  signal closeRequested()
  implicitHeight: body.implicitHeight
  Keys.onEscapePressed: root.closeRequested()

  ColumnLayout {
    id: body
    width: parent.width
    spacing: Theme.Style.space(12)
    RowLayout {
      Layout.fillWidth: true
      Text {
        Layout.fillWidth: true
        text: "Odin2 Portal Hardware"
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
        color: root.foreground
        font.family: Theme.Style.font.family
        font.pixelSize: Theme.Style.font.body
        font.bold: true
      }
      Ui.PanelActionButton {
        objectName: "refreshButton"
        foreground: root.foreground
        iconText: "󰑐"
        tooltipText: "Refresh readings"
        focusable: true
        enabled: !root.service?.busy
        onClicked: if (root.service) root.service.refresh()
      }
      Ui.PanelActionButton {
        foreground: root.foreground
        iconText: "󰅖"
        tooltipText: "Close"
        focusable: true
        onClicked: root.closeRequested()
      }
    }
    Text {
      Layout.fillWidth: true
      visible: !root.readings || !root.supported || root.service?.lastError !== ""
      text: root.service?.lastError || (root.readings
        ? root.readings.reason || "Unsupported device" : "Reading hardware…")
      textFormat: Text.PlainText
      wrapMode: Text.Wrap
      color: root.service?.lastError ? Theme.Color.urgent : root.foreground
      font.family: Theme.Style.font.family
      font.pixelSize: Theme.Style.font.body
    }
    Text {
      Layout.fillWidth: true
      visible: root.service?.stale === true && root.readings !== null
      text: "Showing the last available readings."
      textFormat: Text.PlainText
      wrapMode: Text.Wrap
      color: Theme.Color.urgent
      font.family: Theme.Style.font.family
      font.pixelSize: Theme.Style.font.caption
    }
    Ui.ButtonGroup {
      objectName: "monitorTabs"
      visible: root.supported
      options: [{value: "overview", label: "Overview"},
        {value: "controls", label: "Controls"}, {value: "clocks", label: "Details"}]
      value: root.currentTab === "sensors" ? "clocks" : root.currentTab
      foreground: root.foreground
      onChanged: function(value) { root.currentTab = value }
    }
    ControlsContent {
      id: hardwareControls
      objectName: "hardwareControls"
      visible: root.supported && root.currentTab === "controls"
      Layout.fillWidth: true
      service: root.service
      foreground: root.foreground
    }
    Ui.ButtonGroup {
      visible: root.supported && (root.currentTab === "clocks" || root.currentTab === "sensors")
      foreground: root.foreground
      options: [{value: "clocks", label: "Clocks"}, {value: "sensors", label: "Sensors"}]
      value: root.currentTab
      onChanged: function(value) { root.currentTab = value }
    }
    ColumnLayout {
      visible: root.supported && root.currentTab === "overview"
      Layout.fillWidth: true
      spacing: Theme.Style.space(4)
      Ui.PanelSectionHeader { text: "TEMPERATURE"; foreground: root.foreground }
      StatRow { Layout.fillWidth: true; label: "CPU hottest"; value: Model.format(root.readings?.thermals?.cpu_c, "°C", 1); foreground: root.foreground }
      StatRow { Layout.fillWidth: true; label: "GPU hottest"; value: Model.format(root.readings?.thermals?.gpu_c, "°C", 1); foreground: root.foreground }
      Ui.PanelSeparator { Layout.fillWidth: true; foreground: root.foreground }
      Ui.PanelSectionHeader { text: "FAN"; foreground: root.foreground }
      StatRow { objectName: "fanRpm"; Layout.fillWidth: true; label: "Speed"; value: Model.format(root.readings?.fan?.rpm, " RPM"); foreground: root.foreground }
      StatRow { Layout.fillWidth: true; label: "PWM duty"; value: Model.format(root.readings?.fan?.duty_percent, "%", 1); foreground: root.foreground }
      Ui.PanelSeparator { Layout.fillWidth: true; foreground: root.foreground }
      Ui.PanelSectionHeader { text: "BATTERY"; foreground: root.foreground }
      StatRow { objectName: "batteryCharge"; Layout.fillWidth: true; label: "Charge"; value: Model.format(root.readings?.battery?.capacity_percent, "%"); foreground: root.foreground }
      StatRow { Layout.fillWidth: true; label: "Status"; value: root.readings?.battery?.status || "—"; foreground: root.foreground }
      StatRow { Layout.fillWidth: true; label: "Power"; value: Model.format(root.readings?.battery?.power_w, " W", 1); foreground: root.foreground }
      StatRow { Layout.fillWidth: true; label: "Battery temperature"; value: Model.format(root.readings?.battery?.temperature_c, "°C", 1); foreground: root.foreground }
    }
    ColumnLayout {
      visible: root.supported && root.currentTab === "clocks"
      Layout.fillWidth: true
      spacing: Theme.Style.space(8)
      Repeater {
        model: root.readings?.cpus ?? []
        ColumnLayout {
          required property var modelData
          Layout.fillWidth: true
          Ui.PanelSectionHeader { text: "CPUS " + parent.modelData.cpus.join(", "); foreground: root.foreground }
          StatRow { Layout.fillWidth: true; label: "Current clock"; value: Model.format(parent.modelData.current_mhz, " MHz"); foreground: root.foreground }
          StatRow { Layout.fillWidth: true; label: "Maximum clock"; value: Model.format(parent.modelData.maximum_mhz, " MHz"); foreground: root.foreground }
          StatRow { Layout.fillWidth: true; label: "Governor"; value: Model.governor(parent.modelData.governor); foreground: root.foreground }
          Ui.PanelSeparator { Layout.fillWidth: true; foreground: root.foreground }
        }
      }
      Repeater {
        model: root.readings?.gpus ?? []
        ColumnLayout {
          required property var modelData
          Layout.fillWidth: true
          Ui.PanelSectionHeader { text: "GPU"; foreground: root.foreground }
          StatRow { objectName: "gpuClock"; Layout.fillWidth: true; label: "Current clock"; value: Model.format(parent.modelData.current_mhz, " MHz"); foreground: root.foreground }
          StatRow { Layout.fillWidth: true; label: "Maximum clock"; value: Model.format(parent.modelData.maximum_mhz, " MHz"); foreground: root.foreground }
          StatRow { Layout.fillWidth: true; label: "Governor"; value: Model.governor(parent.modelData.governor); foreground: root.foreground }
        }
      }
    }
    ColumnLayout {
      visible: root.supported && root.currentTab === "sensors"
      Layout.fillWidth: true
      spacing: Theme.Style.space(4)
      Repeater {
        model: root.readings?.thermals?.sensors ?? []
        StatRow {
          required property var modelData
          Layout.fillWidth: true
          label: modelData.name.replace(/-thermal$/, "")
          value: Model.format(modelData.temperature_c, "°C", 1)
          foreground: root.foreground
        }
      }
    }
  }
}
