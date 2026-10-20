// Original, bounded Qt Quick scene inspection. Visual properties only; no eval,
// QObject reflection, external windows, screenshots, input injection or actions.
.pragma library

function finite(value) { return typeof value === "number" && isFinite(value) ? Math.round(value * 10) / 10 : 0 }
function intersect(a, b) {
  var x = Math.max(a.x, b.x), y = Math.max(a.y, b.y)
  return {x: x, y: y, width: Math.max(0, Math.min(a.x + a.width, b.x + b.width) - x),
    height: Math.max(0, Math.min(a.y + a.height, b.y + b.height) - y)}
}
function inspect(root) {
  if (!root) return {nodes: [], truncated: false}
  var nodes = [], truncated = false
  var viewport = {x: 0, y: 0, width: finite(root.width), height: finite(root.height)}
  function visit(item, parent, index, depth, clip, opacity) {
    if (!item || depth > 12 || nodes.length >= 256) { truncated = true; return }
    if (depth > 0 && item.visible !== true) return
    opacity *= typeof item.opacity === "number" ? item.opacity : 1
    var point = item.mapToItem(root, 0, 0)
    var box = {x: finite(point.x), y: finite(point.y), width: finite(item.width), height: finite(item.height)}
    var area = intersect(box, clip)
    var type = String(item).split("(")[0].replace(/_QML_\d+$/, "")
    var name = item.objectName || type + ":" + index
    var path = parent ? parent + "/" + name : name
    var node = {path: path, parent: parent, name: name, type: type, bounds: box,
      visible: item.visible === true, enabled: item.enabled === true,
      in_view: item.visible === true && opacity > 0.01 && area.width > 0 && area.height > 0,
      opacity: finite(opacity),
      focus: item.activeFocus === true}
    if (typeof item.text === "string") node.text = item.text.slice(0, 256)
    if (typeof item.value === "number") node.value = finite(item.value)
    else if (typeof item.value === "string") node.value = item.value.slice(0, 256)
    if (typeof item.checked === "boolean") node.checked = item.checked
    if (typeof item.selected === "boolean") node.selected = item.selected
    if (typeof item.contentY === "number") node.scroll_y = finite(item.contentY)
    nodes.push(node)
    var children = item.children || []
    var childClip = item.clip ? area : clip
    for (var i = 0; i < children.length; i++) visit(children[i], path, i, depth + 1, childClip, opacity)
  }
  visit(root, "", 0, 0, viewport, 1)
  return {viewport: viewport, nodes: nodes, truncated: truncated}
}
