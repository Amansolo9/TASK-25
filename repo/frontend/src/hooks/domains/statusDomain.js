export function toneVariant(tone) {
  if (tone === "success") return "success";
  if (tone === "danger") return "danger";
  return "info";
}

export function statusVariant(value) {
  const safe = String(value || "").toLowerCase();
  if (["live", "success", "active", "closed", "approved", "ok", "confirmed"].includes(safe)) {
    return "success";
  }
  if (["failed", "error", "critical", "rejected", "inactive", "cancelled", "no_show"].includes(safe)) {
    return "danger";
  }
  if (["pending", "review", "blocked", "waitlisted", "warning", "draft", "running"].includes(safe)) {
    return "warning";
  }
  return "default";
}

export function getFirstScreenForRoles(roles, roleScreens) {
  const available = new Set();
  (roles || []).forEach((role) => {
    (roleScreens[role.code] || []).forEach((screen) => {
      available.add(screen);
    });
  });
  if (available.has("Trips")) return "Trips";
  return Array.from(available)[0] || "Trips";
}
