import QtQuick
import Quickshell
import qs.Commons as Theme
import qs.Ui as Ui
import "Scene.js" as Scene

Ui.Panel {
  id: root
  moduleName: "io.github.techluddite.odin2-portal-hardware"
  manageIpc: false
  property var service: null
  property var anchorItem: null
  property var hostWidget: null
  readonly property Item form: monitor
  onOpenedChanged: if (service) service.watch(root, opened)
  onServiceChanged: if (service) { service.watch(root, opened); service.panelRoot = root }
  Component.onDestruction: if (service) {
    service.watch(root, false)
    if (service.panelRoot === root) service.panelRoot = null
  }
  function inspect() {
    return {schema_version: 1, panel: "hardware", open: root.opened,
      tab: monitor.currentTab, section: monitor.controlsView.section,
      window: {width: popup.width, height: popup.height},
      scroll: {y: viewport.contentY, height: viewport.height, content_height: viewport.contentHeight},
      scene: Scene.inspect(viewport)}
  }
  function navigate(request) {
    if (!request || typeof request !== "object" || Array.isArray(request)) return {error: "Expected an object"}
    var allowed = {open: ["op"], close: ["op"], tab: ["op", "value"], section: ["op", "value"], scroll: ["op", "value"]}
    if (!allowed[request.op] || Object.keys(request).some(function(key) { return allowed[request.op].indexOf(key) < 0 }))
      return {error: "Unknown navigation operation or field"}
    if (request.op === "open") root.hostWidget ? root.hostWidget.open() : root.open()
    else if (request.op === "close") root.close()
    else if (request.op === "tab") {
      if (["overview", "controls", "clocks", "sensors"].indexOf(request.value) < 0) return {error: "Unknown tab"}
      monitor.currentTab = request.value
    } else if (request.op === "section") {
      if (["power", "fan", "lights"].indexOf(request.value) < 0) return {error: "Unknown control section"}
      monitor.currentTab = "controls"
      monitor.controlsView.section = request.value
    } else {
      if (typeof request.value !== "number" || !isFinite(request.value)) return {error: "Expected a finite scroll position"}
      viewport.contentY = Math.max(0, Math.min(request.value, Math.max(0, viewport.contentHeight - viewport.height)))
    }
    return {ok: true}
  }

  Ui.KeyboardPanel {
    id: popup
    anchorItem: root.anchorItem
    owner: root.hostWidget || root
    bar: root.bar
    open: root.opened
    focusTarget: monitor
    contentWidth: popup.fittedContentWidth(Theme.Style.space(480))
    contentHeight: popup.fittedContentHeight(monitor.implicitHeight)
    Flickable {
      id: viewport
      objectName: "hardwareViewport"
      anchors.fill: parent
      contentWidth: width
      contentHeight: monitor.implicitHeight
      clip: true
      boundsBehavior: Flickable.StopAtBounds
      MonitorContent {
        id: monitor
        width: parent.width
        service: root.service
        // Popup surfaces must not inherit adaptive transparent-bar text.
        foreground: Theme.Color.popups.text
        onCloseRequested: root.close()
      }
    }
  }
}
