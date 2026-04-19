import { useCallback } from "react";

function jsonOptions(method, payload) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  };
}

export function useProfileActions({
  api,
  setStatus,
  loadAlerts,
  loadFavorites,
  loadComparisons,
  loadTravelerProfiles,
  loadExportRequests,
  profileForms,
  setProfileForms,
  setProfileError,
  setPreference,
  setTravelerReveal,
}) {
  const postJson = useCallback((path, payload) => api(path, jsonOptions("POST", payload), true), [api]);
  const putJson = useCallback((path, payload) => api(path, jsonOptions("PUT", payload), true), [api]);
  const deleteWithCsrf = useCallback((path) => api(path, { method: "DELETE" }, true), [api]);
  const setDangerStatus = useCallback(
    (error) => setStatus({ loading: false, message: error.message, tone: "danger" }),
    [setStatus]
  );

  const createFavorite = useCallback(
    async (event) => {
      event.preventDefault();
      try {
        await postJson("/api/auth/favorites/", {
          kind: profileForms.favoriteKind,
          reference_id: profileForms.favoriteRef,
        });
        setProfileForms((prev) => ({ ...prev, favoriteRef: "" }));
        await loadFavorites();
        setStatus({ loading: false, message: "Favorite saved", tone: "success" });
      } catch (error) {
        setDangerStatus(error);
      }
    },
    [
      loadFavorites,
      postJson,
      profileForms.favoriteKind,
      profileForms.favoriteRef,
      setDangerStatus,
      setProfileForms,
      setStatus,
    ]
  );

  const deleteFavorite = useCallback(
    async (favoriteId) => {
      try {
        await deleteWithCsrf(`/api/auth/favorites/${favoriteId}/`);
        await loadFavorites();
      } catch (error) {
        setDangerStatus(error);
      }
    },
    [deleteWithCsrf, loadFavorites, setDangerStatus]
  );

  const createComparison = useCallback(
    async (event) => {
      event.preventDefault();
      try {
        await postJson("/api/auth/comparisons/", {
          kind: profileForms.comparisonKind,
          reference_id: profileForms.comparisonRef,
        });
        setProfileForms((prev) => ({ ...prev, comparisonRef: "" }));
        await loadComparisons();
        setStatus({ loading: false, message: "Comparison item added", tone: "success" });
      } catch (error) {
        setDangerStatus(error);
      }
    },
    [
      loadComparisons,
      postJson,
      profileForms.comparisonKind,
      profileForms.comparisonRef,
      setDangerStatus,
      setProfileForms,
      setStatus,
    ]
  );

  const deleteComparison = useCallback(
    async (comparisonId) => {
      try {
        await deleteWithCsrf(`/api/auth/comparisons/${comparisonId}/`);
        await loadComparisons();
      } catch (error) {
        setDangerStatus(error);
      }
    },
    [deleteWithCsrf, loadComparisons, setDangerStatus]
  );

  const createReminder = useCallback(
    async (event) => {
      event.preventDefault();
      try {
        await postJson("/api/auth/alerts/", {
          title: profileForms.reminderTitle,
          message: profileForms.reminderMessage,
        });
        setProfileForms((prev) => ({ ...prev, reminderTitle: "", reminderMessage: "" }));
        await loadAlerts();
        setStatus({ loading: false, message: "Reminder created", tone: "success" });
      } catch (error) {
        setDangerStatus(error);
      }
    },
    [
      loadAlerts,
      postJson,
      profileForms.reminderMessage,
      profileForms.reminderTitle,
      setDangerStatus,
      setProfileForms,
      setStatus,
    ]
  );

  const acknowledgeReminder = useCallback(
    async (alertId) => {
      try {
        await postJson(`/api/auth/alerts/${alertId}/acknowledge/`, {});
        await loadAlerts();
      } catch (error) {
        setDangerStatus(error);
      }
    },
    [loadAlerts, postJson, setDangerStatus]
  );

  const updatePreference = useCallback(
    async (event) => {
      event.preventDefault();
      setProfileError("");
      try {
        const data = await putJson("/api/auth/preferences/", {
          locale: profileForms.prefLocale,
          timezone: profileForms.prefTimezone,
          large_text_mode: Boolean(profileForms.prefLargeText),
          high_contrast_mode: Boolean(profileForms.prefHighContrast),
        });
        setPreference(data);
        setStatus({ loading: false, message: "Preferences updated", tone: "success" });
      } catch (error) {
        setProfileError(error.message);
      }
    },
    [
      profileForms.prefHighContrast,
      profileForms.prefLargeText,
      profileForms.prefLocale,
      profileForms.prefTimezone,
      putJson,
      setPreference,
      setProfileError,
      setStatus,
    ]
  );

  const saveTravelerProfile = useCallback(
    async (event) => {
      event.preventDefault();
      setProfileError("");
      try {
        await postJson("/api/auth/traveler-profiles/", {
          display_name: profileForms.travelerDisplayName,
          identifier: profileForms.travelerIdentifier,
          government_id: profileForms.travelerGovernmentId,
          credential_number: profileForms.travelerCredentialNumber,
        });
        setProfileForms((prev) => ({
          ...prev,
          travelerDisplayName: "",
          travelerIdentifier: "",
          travelerGovernmentId: "",
          travelerCredentialNumber: "",
        }));
        await loadTravelerProfiles();
        setStatus({ loading: false, message: "Traveler profile saved", tone: "success" });
      } catch (error) {
        setProfileError(error.message);
      }
    },
    [
      loadTravelerProfiles,
      postJson,
      profileForms.travelerCredentialNumber,
      profileForms.travelerDisplayName,
      profileForms.travelerGovernmentId,
      profileForms.travelerIdentifier,
      setProfileError,
      setProfileForms,
      setStatus,
    ]
  );

  const revealTravelerField = useCallback(
    async (profileId, sensitiveField, reason = "") => {
      setProfileError("");
      if (!reason.trim()) {
        setProfileError("Reason is required to reveal sensitive traveler fields.");
        return;
      }
      try {
        await postJson("/api/security/unmask-sessions/", {
          field_name: `traveler_${sensitiveField.replace("-", "_")}:${profileId}`,
          reason,
          minutes: 5,
        });
        const data = await api(`/api/security/traveler-profiles/${profileId}/reveal/${sensitiveField}/`);
        const revealedValue = Object.values(data || {})[0] || "";
        setTravelerReveal((prev) => ({ ...prev, [profileId]: revealedValue }));
      } catch (error) {
        setProfileError(error.message);
      }
    },
    [api, postJson, setProfileError, setTravelerReveal]
  );

  const requestExport = useCallback(
    async (event) => {
      event.preventDefault();
      setProfileError("");
      if (profileForms.exportIncludeUnmasked && !String(profileForms.exportJustification || "").trim()) {
        setProfileError("Justification is required for unmasked export requests.");
        return;
      }
      try {
        await postJson("/api/auth/exports/request/", {
          include_unmasked: Boolean(profileForms.exportIncludeUnmasked),
          justification: profileForms.exportJustification,
          format: profileForms.exportFormat || "json",
        });
        await loadExportRequests();
        setStatus({ loading: false, message: "Export request submitted", tone: "success" });
      } catch (error) {
        setProfileError(error.message);
      }
    },
    [
      loadExportRequests,
      postJson,
      profileForms.exportFormat,
      profileForms.exportIncludeUnmasked,
      profileForms.exportJustification,
      setProfileError,
      setStatus,
    ]
  );

  const submitDeletionRequest = useCallback(
    async (event) => {
      event.preventDefault();
      setProfileError("");
      if (!profileForms.retentionAcknowledged) {
        setProfileError("You must acknowledge the retention notice before requesting deletion.");
        return;
      }
      try {
        await postJson("/api/auth/deletion-request/", {
          retention_notice: profileForms.deletionRetentionNotice,
        });
        setStatus({ loading: false, message: "Account deletion requested", tone: "warning" });
      } catch (error) {
        setProfileError(error.message);
      }
    },
    [
      postJson,
      profileForms.deletionRetentionNotice,
      profileForms.retentionAcknowledged,
      setProfileError,
      setStatus,
    ]
  );

  return {
    createFavorite,
    deleteFavorite,
    createComparison,
    deleteComparison,
    createReminder,
    acknowledgeReminder,
    updatePreference,
    saveTravelerProfile,
    revealTravelerField,
    requestExport,
    submitDeletionRequest,
  };
}
