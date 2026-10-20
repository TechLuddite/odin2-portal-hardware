import QtQuick
import Quickshell
import Quickshell.Io

Item {
  id: root
  property var shell: null
  property var panelRoot: null
  property var manifest: null
  property var snapshot: null
  property string lastError: ""
  property var readers: []
  property double sampledAt: 0
  property bool timedOut: false
  property string sessionToken: "portal_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2) + "_panel"
  property var controls: snapshot?.controls ?? ({available: false})
  property string controlError: ""
  property bool controlling: writer.running
  property string requestPayload: ""
  property double leaseTouchedAt: 0
  property var controlCommand: ["/usr/bin/python3", "-I", "-B",
    Qt.resolvedUrl("bin/odin2-portal-hardware").toString().replace(/^file:\/\//, "")]
  readonly property bool busy: reader.running
  readonly property bool supported: snapshot?.supported === true
  readonly property bool stale: lastError !== ""
  // An explicit argv also lets the isolated fixture run a fake sysfs tree.
  property var readerCommand: ["/usr/bin/python3", "-I", "-B",
    Qt.resolvedUrl("bin/odin2-portal-hardware").toString().replace(/^file:\/\//, ""), "--session", root.sessionToken]

  function control(request) {
    if (writer.running) return
    request.token = root.sessionToken
    root.requestPayload = JSON.stringify(request)
    root.leaseTouchedAt = Date.now()
    root.controlError = ""
    writer.running = true
  }

  function refresh() {
    if (!reader.running) {
      root.timedOut = false
      reader.running = true
      deadline.restart()
    }
  }
  function watch(client, active) {
    var next = root.readers.filter(function(item) { return item !== client })
    if (active) next.push(client)
    root.readers = next
    if (active) root.refresh()
  }
  function accept(text) {
    if (text.length > 65536) {
      root.lastError = "Hardware response was too large."
      return
    }
    try {
      var value = JSON.parse(text)
      if (value.schema_version !== 1 || typeof value.supported !== "boolean"
          || !Array.isArray(value.cpus) || !Array.isArray(value.gpus)
          || !Array.isArray(value.thermals?.sensors)
          || !value.fan || !value.battery) throw new Error("schema")
      root.snapshot = value
      root.sampledAt = Date.now()
      root.lastError = ""
    } catch (error) {
      root.lastError = "Hardware readings are unavailable."
    }
  }
  Timer {
    interval: root.controls?.owned || Date.now() - root.leaseTouchedAt < 15000 || root.readers.length ? 3000 : 15000
    running: true
    repeat: true
    onTriggered: root.refresh()
  }
  Timer {
    id: deadline
    interval: 5000
    onTriggered: {
      root.lastError = "Hardware reader timed out."
      root.timedOut = true
      reader.signal(15)
    }
  }
  Process {
    id: writer
    command: root.controlCommand.concat(["--request", root.requestPayload])
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          if (text.length > 65536) throw new Error("size")
          var result = JSON.parse(text)
          root.controlError = result.error || ""
          if (root.snapshot) root.snapshot = Object.assign({}, root.snapshot, {controls: result})
        } catch (error) { root.controlError = "Invalid response from hardware helper." }
      }
    }
    onExited: function(code, status) {
      if (code !== 0 || status !== 0) root.controlError = "Hardware control request failed."
      root.refresh()
    }
  }
  Process {
    id: reader
    command: root.readerCommand
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: if (!root.timedOut) root.accept(text)
    }
    onExited: function(code, status) {
      deadline.stop()
      if ((code !== 0 || status !== 0) && root.lastError === "")
        root.lastError = "Hardware reader stopped unexpectedly."
    }
  }
  IpcHandler {
    target: "odin2-portal-hardware"
    function refresh(): void { root.refresh() }
    function status(): string {
      return JSON.stringify({supported: root.supported, access: root.snapshot?.access ?? "read-only",
        sampled: root.sampledAt > 0, stale: root.stale, busy: root.busy,
        error: root.lastError, controls_available: root.controls?.available === true,
        controls: root.controls, control_error: root.controlError})
    }
    function control(request: string): void {
      try { root.control(JSON.parse(request)) }
      catch (error) { root.controlError = "Invalid hardware control request." }
    }
    function inspect(): string {
      var result = root.panelRoot ? root.panelRoot.inspect() : {schema_version: 1, panel: "hardware", open: false, error: "Panel is not loaded"}
      result.sampled_at = root.sampledAt
      result.stale = root.stale
      result.error = result.error || root.lastError || root.controlError
      result.controls = root.controls
      return JSON.stringify(result)
    }
    function navigate(request: string): string {
      try {
        if (request.length > 2048) return JSON.stringify({error: "Navigation request too large"})
        return JSON.stringify(root.panelRoot ? root.panelRoot.navigate(JSON.parse(request)) : {error: "Panel is not loaded"})
      } catch (error) { return JSON.stringify({error: "Invalid navigation request"}) }
    }
  }
  Component.onCompleted: refresh()
}
