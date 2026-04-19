import { useCallback, useState } from "react";

import { initialProfileForms } from "./domains/profileDomain";

export function useProfileDataLoaders({ api }) {
  const [favorites, setFavorites] = useState([]);
  const [comparisons, setComparisons] = useState([]);
  const [preference, setPreference] = useState(null);
  const [travelerProfiles, setTravelerProfiles] = useState([]);
  const [travelerReveal, setTravelerReveal] = useState({});
  const [exportRequests, setExportRequests] = useState([]);
  const [profileError, setProfileError] = useState("");
  const [profileForms, setProfileForms] = useState(initialProfileForms);

  const loadFavorites = useCallback(async () => {
    try {
      const data = await api("/api/auth/favorites/");
      setFavorites(data || []);
    } catch {
      setFavorites([]);
    }
  }, [api]);

  const loadComparisons = useCallback(async () => {
    try {
      const data = await api("/api/auth/comparisons/");
      setComparisons(data || []);
    } catch {
      setComparisons([]);
    }
  }, [api]);

  const loadPreference = useCallback(async () => {
    try {
      const data = await api("/api/auth/preferences/");
      setPreference(data || null);
      if (data) {
        setProfileForms((prev) => ({
          ...prev,
          prefLocale: data.locale || "en",
          prefTimezone: data.timezone || "UTC",
          prefLargeText: Boolean(data.large_text_mode),
          prefHighContrast: Boolean(data.high_contrast_mode),
        }));
      }
    } catch {
      setPreference(null);
    }
  }, [api]);

  const loadTravelerProfiles = useCallback(async () => {
    try {
      const data = await api("/api/auth/traveler-profiles/");
      setTravelerProfiles(data || []);
    } catch {
      setTravelerProfiles([]);
    }
  }, [api]);

  const loadExportRequests = useCallback(async () => {
    try {
      const data = await api("/api/auth/exports/");
      setExportRequests(data || []);
    } catch {
      setExportRequests([]);
    }
  }, [api]);

  const resetProfileData = useCallback(() => {
    setFavorites([]);
    setComparisons([]);
    setPreference(null);
    setTravelerProfiles([]);
    setTravelerReveal({});
    setExportRequests([]);
    setProfileError("");
    setProfileForms(initialProfileForms);
  }, []);

  return {
    favorites,
    comparisons,
    preference,
    travelerProfiles,
    travelerReveal,
    exportRequests,
    profileError,
    profileForms,
    setProfileForms,
    setProfileError,
    setPreference,
    setTravelerReveal,
    loadFavorites,
    loadComparisons,
    loadPreference,
    loadTravelerProfiles,
    loadExportRequests,
    resetProfileData,
  };
}
