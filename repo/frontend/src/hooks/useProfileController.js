import { useMemo } from "react";

import { canRequestUnmaskedByRoles } from "./domains/profileDomain";
import { useProfileActions } from "./useProfileActions";
import { useProfileDataLoaders } from "./useProfileDataLoaders";

export function useProfileController({ api, setStatus, sessionRoles, loadAlerts }) {
  const data = useProfileDataLoaders({ api });

  const actions = useProfileActions({
    api,
    setStatus,
    loadAlerts,
    loadFavorites: data.loadFavorites,
    loadComparisons: data.loadComparisons,
    loadTravelerProfiles: data.loadTravelerProfiles,
    loadExportRequests: data.loadExportRequests,
    profileForms: data.profileForms,
    setProfileForms: data.setProfileForms,
    setProfileError: data.setProfileError,
    setPreference: data.setPreference,
    setTravelerReveal: data.setTravelerReveal,
  });

  const canRequestUnmasked = useMemo(
    () => canRequestUnmaskedByRoles(sessionRoles),
    [sessionRoles]
  );

  return {
    favorites: data.favorites,
    comparisons: data.comparisons,
    preference: data.preference,
    travelerProfiles: data.travelerProfiles,
    travelerReveal: data.travelerReveal,
    exportRequests: data.exportRequests,
    profileError: data.profileError,
    profileForms: data.profileForms,
    setProfileForms: data.setProfileForms,
    canRequestUnmasked,
    loadFavorites: data.loadFavorites,
    loadComparisons: data.loadComparisons,
    loadPreference: data.loadPreference,
    loadTravelerProfiles: data.loadTravelerProfiles,
    loadExportRequests: data.loadExportRequests,
    createFavorite: actions.createFavorite,
    deleteFavorite: actions.deleteFavorite,
    createComparison: actions.createComparison,
    deleteComparison: actions.deleteComparison,
    createReminder: actions.createReminder,
    acknowledgeReminder: actions.acknowledgeReminder,
    updatePreference: actions.updatePreference,
    saveTravelerProfile: actions.saveTravelerProfile,
    revealTravelerField: actions.revealTravelerField,
    requestExport: actions.requestExport,
    submitDeletionRequest: actions.submitDeletionRequest,
    resetProfile: data.resetProfileData,
  };
}
