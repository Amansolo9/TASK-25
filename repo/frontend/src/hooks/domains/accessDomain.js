const roleCapabilities = {
  senior: {
    screens: ["Trips", "Profile"],
    actions: ["trip.book", "trip.track", "profile.manage", "verification.submit"],
  },
  family_member: {
    screens: ["Trips", "Profile"],
    actions: ["trip.book", "trip.track", "profile.manage", "verification.submit"],
  },
  caregiver: {
    screens: ["Trips", "Profile"],
    actions: ["trip.book", "trip.track", "trip.manage", "profile.manage", "verification.submit"],
  },
  org_admin: {
    screens: ["Trips", "Warehouse", "Inventory", "Jobs", "Verification", "Anomalies", "Profile"],
    actions: [
      "trip.book",
      "trip.track",
      "trip.manage",
      "warehouse.manage",
      "inventory.manage",
      "jobs.manage",
      "verification.review",
      "profile.manage",
      "sensitive.unmask",
    ],
  },
  platform_admin: {
    screens: [
      "Trips",
      "Warehouse",
      "Inventory",
      "Jobs",
      "Verification",
      "Anomalies",
      "Profile",
      "Cross-Org Oversight",
      "Security",
    ],
    actions: [
      "trip.book",
      "trip.track",
      "trip.manage",
      "warehouse.manage",
      "inventory.manage",
      "jobs.manage",
      "verification.review",
      "profile.manage",
      "sensitive.unmask",
      "crossorg.view",
    ],
  },
};

export function getCapabilities(roles = []) {
  const screens = new Set();
  const actions = new Set();
  roles.forEach((role) => {
    const caps = roleCapabilities[role.code];
    (caps?.screens || []).forEach((screen) => screens.add(screen));
    (caps?.actions || []).forEach((action) => actions.add(action));
  });
  return {
    screens: Array.from(screens),
    actions,
  };
}

export function canAccessScreen(capabilities, screenName) {
  return capabilities.screens.includes(screenName);
}

export function canPerform(capabilities, actionCode) {
  return capabilities.actions.has(actionCode);
}
