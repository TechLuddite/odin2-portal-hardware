import QtQuick
import qs.Commons as Theme
import qs.Ui as Ui
import "Model.js" as Model

Ui.BarWidget {
  id: root
  moduleName: "io.github.techluddite.odin2-portal-hardware"
  readonly property var service: bar?.shell?.serviceFor(root.moduleName) ?? null
  readonly property var panel: detail
  readonly property bool opened: detail.opened
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight
  property bool popoutSwitchClosing: false

  function open() {
    root.injectPanel()
    detail.open()
  }
  function close() { detail.close() }
  function togglePanel() { opened ? close() : open() }
  function closeForPopoutSwitch() { detail.closeForPopoutSwitch() }
  function injectPanel() {
    detail.bar = root.bar
    detail.settings = root.settings
  }
  onBarChanged: injectPanel()
  onSettingsChanged: injectPanel()

  Panel {
    id: detail
    service: root.service
    anchorItem: button
    hostWidget: root
    bar: root.bar
    settings: root.settings
  }
  Ui.BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "󰈐"
    tooltipText: root.service?.lastError || (!root.service?.supported
      ? "Odin2 Portal Hardware — waiting for Portal readings"
      : "Portal · " + Model.format(Model.temperature(root.service.snapshot), "°C", 1)
        + " · " + Model.format(root.service.snapshot?.fan?.rpm, " RPM"))
    foreground: root.service?.lastError ? Theme.Color.urgent
      : (root.bar ? root.bar.barForeground : Theme.Color.foreground)
    onPressed: function(button) {
      if (button === Qt.RightButton && root.service) root.service.refresh()
      else if (button === Qt.LeftButton) root.togglePanel()
    }
  }
}
