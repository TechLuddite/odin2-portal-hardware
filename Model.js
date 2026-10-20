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
