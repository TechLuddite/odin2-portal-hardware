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
function presetDetails(plan, snapshot) {
  if (!plan) return "Advertised preset data is unavailable."
  var lines = []
  for (var cpu of plan.cpus || []) {
    lines.push("CPU " + (cpu.cpus || []).join(", ") + " · " + governor(cpu.governor)
      + "\n" + range(cpu.minimum_mhz, cpu.maximum_mhz) + " · hard ceiling " + mhz(cpu.maximum_mhz)
      + "\n" + (cpu.minimum_equals_maximum ? "Minimum equals maximum: fixed range."
        : cpu.behavior === "requests-ceiling" ? "Requests the ceiling; minimum is not pinned to maximum."
        : "Scales through advertised steps with load."))
  }
  var gpu = (snapshot?.gpus || [])[0]
  lines.push("GPU · hard ceiling " + mhz(plan.gpu_maximum_mhz)
    + "\nGovernor unchanged (now " + governor(gpu?.governor) + "); minimum unchanged (now " + mhz(gpu?.minimum_mhz) + ").")
  var storage = (snapshot?.storage || [])[0]
  lines.push("UFS storage · unchanged by this level"
    + (storage ? "\n" + governor(storage.governor) + " · " + range(storage.minimum_mhz, storage.maximum_mhz)
      + "\nAdvertised steps: " + storage.available_mhz.map(function(v) { return mhz(v) }).join(", ") : "\nLive storage data unavailable."))
  lines.push("Fan mode and RGB are unchanged by power levels. Thermal and other hardware limits can override clock requests.")
  return lines.join("\n\n")
}
function liveClocks(snapshot) {
  var lines = []
  for (var cpu of snapshot?.cpus || [])
    lines.push("CPU " + (cpu.cpus || []).join(", ") + ": " + governor(cpu.governor) + " · " + mhz(cpu.current_mhz))
  for (var gpu of snapshot?.gpus || []) lines.push("GPU: " + governor(gpu.governor) + " · " + mhz(gpu.current_mhz))
  for (var storage of snapshot?.storage || []) lines.push("UFS: " + governor(storage.governor) + " · " + mhz(storage.current_mhz))
  return lines.join("\n")
}
