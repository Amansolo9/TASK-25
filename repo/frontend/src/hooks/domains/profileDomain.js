export const initialProfileForms = {
  favoriteKind: "trip",
  favoriteRef: "",
  comparisonKind: "plan",
  comparisonRef: "",
  reminderTitle: "",
  reminderMessage: "",
  prefLocale: "en",
  prefTimezone: "UTC",
  prefLargeText: false,
  prefHighContrast: false,
  travelerDisplayName: "",
  travelerIdentifier: "",
  travelerGovernmentId: "",
  travelerCredentialNumber: "",
  revealReason: "",
  revealTargetProfileId: "",
  revealTargetField: "identifier",
  retentionAcknowledged: false,
  exportIncludeUnmasked: false,
  exportJustification: "",
  exportFormat: "json",
  deletionRetentionNotice: "",
};

export function canRequestUnmaskedByRoles(roles) {
  return (roles || []).some((role) => ["org_admin", "platform_admin"].includes(role.code));
}
