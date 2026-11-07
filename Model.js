.pragma library

function format(value, unit, digits) {
  if (typeof value !== "number" || !isFinite(value)) return "—"
  return value.toFixed(digits === undefined ? 0 : digits) + (unit || "")
}

function governor(value) {
  return {performance: "Performance", powersave: "Power saver", schedutil: "Schedutil",
    ondemand: "On demand", simple_ondemand: "On demand", userspace: "Userspace"}[value] || value || "—"
}

function temperature(snapshot) {
  var values = [snapshot?.thermals?.cpu_c, snapshot?.thermals?.gpu_c]
    .filter(function(v) { return typeof v === "number" && isFinite(v) })
  return values.length ? Math.max.apply(Math, values) : null
}


function mhz(value) { return format(value, " MHz", value % 1 ? 1 : 0) }
function range(minimum, maximum) { return mhz(minimum) + " – " + mhz(maximum) }
function ceiling(value, unit) {
  if (value === null || value === undefined) return "—"
  return unit === "GHz" ? (value / 1000).toFixed(2) : String(Math.round(value))
}
// One row per level: CPU cluster ceilings in GHz, then the GPU ceiling in MHz.
function presetTable(presets) {
  var labels = {saver: "Save", balanced: "Balanced", performance: "Full"}
  return (presets || []).map(function(plan) {
    return {mode: plan.mode, label: labels[plan.mode] || plan.mode,
      cells: (plan.cpus || []).map(function(cpu) { return ceiling(cpu.maximum_mhz, "GHz") })
        .concat([ceiling(plan.gpu_maximum_mhz, "MHz")])}
  })
}
function presetColumns(presets) {
  var first = (presets || [])[0]
  return ["Level"].concat((first?.cpus || []).map(function(cpu) {
    var ids = cpu.cpus || []
    return "CPU " + (ids.length > 1 ? ids[0] + "–" + ids[ids.length - 1] : ids[0])
  })).concat(["GPU"])
}
function liveClocks(snapshot) {
  var lines = []
  for (var cpu of snapshot?.cpus || [])
    lines.push("CPU " + (cpu.cpus || []).join(", ") + ": " + governor(cpu.governor) + " · " + mhz(cpu.current_mhz))
  for (var gpu of snapshot?.gpus || []) lines.push("GPU: " + governor(gpu.governor) + " · " + mhz(gpu.current_mhz))
  for (var storage of snapshot?.storage || []) lines.push("UFS: " + governor(storage.governor) + " · " + mhz(storage.current_mhz))
  return lines.join("\n")
}
