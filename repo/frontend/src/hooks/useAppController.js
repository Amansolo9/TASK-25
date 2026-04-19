import { useCallback, useEffect, useMemo, useState } from "react";

import { getCapabilities } from "./domains/accessDomain";
import { getFirstScreenForRoles, statusVariant, toneVariant } from "./domains/statusDomain";
import { useJobsController } from "./useJobsController";
import { useOperationsController } from "./useOperationsController";
import { useProfileController } from "./useProfileController";
import { useTripsController } from "./useTripsController";
import { createApiClient } from "../services/apiClient";

const initialAuth = { username: "orgadmin", password: "SecurePass1234" };
const initialRegisterForm = {
  organization_code: "",
  username: "",
  password: "",
  real_name: "",
};
const initialChangePasswordForm = { current_password: "", new_password: "" };

function passwordPolicyMessage(password) {
  const hasLength = String(password || "").length >= 12;
  const hasLetter = /[A-Za-z]/.test(password || "");
  const hasNumber = /\d/.test(password || "");
  if (hasLength && hasLetter && hasNumber) return "Password policy looks good.";
  return "Use at least 12 characters with letters and numbers.";
}

export function useAppController({ apiBaseUrl, roleScreens }) {
  const [auth, setAuth] = useState(initialAuth);
  const [registerForm, setRegisterForm] = useState(initialRegisterForm);
  const [changePasswordForm, setChangePasswordForm] = useState(initialChangePasswordForm);
  const [session, setSession] = useState({ me: null, roles: [] });
  const [activeScreen, setActiveScreen] = useState("Trips");
  const [status, setStatus] = useState({
    loading: false,
    message: "Checking backend...",
    tone: "info",
  });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshAt, setLastRefreshAt] = useState(null);
  const [authMode, setAuthMode] = useState("login");
  const [captcha, setCaptcha] = useState({ required: false, challengeId: "", prompt: "", response: "" });
  const [lockedUntil, setLockedUntil] = useState("");

  const healthUrl = useMemo(() => `${apiBaseUrl}/api/health/`, [apiBaseUrl]);
  const apiClient = useMemo(() => createApiClient(apiBaseUrl), [apiBaseUrl]);

  useEffect(() => {
    fetch(healthUrl)
      .then((response) => response.json())
      .then(() => setStatus({ loading: false, message: "Backend connected", tone: "success" }))
      .catch(() => setStatus({ loading: false, message: "Backend unavailable", tone: "danger" }));
  }, [healthUrl]);

  const api = useCallback(
    (path, options = {}, includeCsrf = false) => apiClient.request(path, options, includeCsrf),
    [apiClient]
  );

  const trips = useTripsController({ api, setStatus });
  const operations = useOperationsController({ api, setStatus });
  const jobs = useJobsController({ api, setStatus });
  const profile = useProfileController({
    api,
    setStatus,
    sessionRoles: session.roles,
    loadAlerts: operations.loadAlerts,
  });

  const capabilities = useMemo(() => getCapabilities(session.roles), [session.roles]);
  const registrationPasswordPolicy = useMemo(
    () => passwordPolicyMessage(registerForm.password),
    [registerForm.password]
  );

  const refreshData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([
        trips.loadTrips(),
        trips.loadMyBookings(),
        operations.loadWarehouses(),
        operations.loadZones(),
        operations.loadLocations(),
        operations.loadPartners(),
        operations.loadPlans(),
        operations.loadInventoryTasks(),
        operations.loadInventoryLines(),
        jobs.loadJobs(),
        operations.loadVerificationRequests(),
        operations.loadAlerts(),
        profile.loadFavorites(),
        profile.loadComparisons(),
        profile.loadPreference(),
        profile.loadTravelerProfiles(),
        profile.loadExportRequests(),
      ]);
      setLastRefreshAt(new Date());
    } finally {
      setIsRefreshing(false);
    }
  }, [jobs, operations, profile, trips]);

  const requestCaptchaChallenge = useCallback(async () => {
    const response = await api(
      "/api/auth/captcha/challenge/",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: auth.username }),
      },
      true
    );
    setCaptcha((prev) => ({
      ...prev,
      required: true,
      challengeId: response.challenge_id,
      prompt: response.prompt,
      response: "",
    }));
  }, [api, auth.username]);

  const handleLogin = useCallback(
    async (event) => {
      event.preventDefault();
      setStatus({ loading: true, message: "Signing in...", tone: "info" });
      setLockedUntil("");
      try {
        const csrfToken = await apiClient.fetchCsrfToken();
        const loginResponse = await fetch(`${apiBaseUrl}/api/auth/login/`, {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({
            ...auth,
            captcha_challenge_id: captcha.challengeId || undefined,
            captcha_response: captcha.response || undefined,
          }),
        });
        const payload = await loginResponse.json();

        if (!loginResponse.ok) {
          if (payload.requires_captcha) {
            await requestCaptchaChallenge();
          }
          if (payload.locked_until) {
            setLockedUntil(payload.locked_until);
          }
          throw new Error(payload.detail || "Login failed");
        }

        const me = payload;
        const rolesResponse = await fetch(`${apiBaseUrl}/api/access/me/roles/`, {
          credentials: "include",
        });
        const roles = rolesResponse.ok ? await rolesResponse.json() : [];

        setSession({ me, roles });
        setActiveScreen(getFirstScreenForRoles(roles, roleScreens));
        setCaptcha({ required: false, challengeId: "", prompt: "", response: "" });
        setStatus({ loading: false, message: "Signed in successfully", tone: "success" });
        await refreshData();
      } catch (error) {
        setStatus({ loading: false, message: error.message, tone: "danger" });
      }
    },
    [apiBaseUrl, apiClient, auth, captcha.challengeId, captcha.response, refreshData, requestCaptchaChallenge, roleScreens]
  );

  const handleRegister = useCallback(
    async (event) => {
      event.preventDefault();
      setStatus({ loading: true, message: "Creating account...", tone: "info" });
      try {
        await api(
          "/api/auth/register/",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(registerForm),
          },
          true
        );
        setRegisterForm(initialRegisterForm);
        setAuth((prev) => ({ ...prev, username: registerForm.username, password: "" }));
        setAuthMode("login");
        setStatus({ loading: false, message: "Registration complete. Please sign in.", tone: "success" });
      } catch (error) {
        setStatus({ loading: false, message: error.message, tone: "danger" });
      }
    },
    [api, registerForm]
  );

  const handleChangePassword = useCallback(
    async (event) => {
      event.preventDefault();
      setStatus({ loading: true, message: "Updating password...", tone: "info" });
      try {
        await api(
          "/api/auth/change-password/",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(changePasswordForm),
          },
          true
        );
        setChangePasswordForm(initialChangePasswordForm);
        setStatus({ loading: false, message: "Password updated.", tone: "success" });
      } catch (error) {
        setStatus({ loading: false, message: error.message, tone: "danger" });
      }
    },
    [api, changePasswordForm]
  );

  const handleLogout = useCallback(async () => {
    try {
      await api("/api/auth/logout/", { method: "POST" }, true);
    } catch {
      // no-op
    }
    setSession({ me: null, roles: [] });
    setAuth(initialAuth);
    setCaptcha({ required: false, challengeId: "", prompt: "", response: "" });
    setLockedUntil("");
    trips.resetTrips();
    operations.resetOperations();
    jobs.resetJobs();
    profile.resetProfile();
    setStatus({ loading: false, message: "Signed out", tone: "info" });
  }, [api, jobs, operations, profile, trips]);

  return {
    auth,
    setAuth,
    registerForm,
    setRegisterForm,
    registrationPasswordPolicy,
    changePasswordForm,
    setChangePasswordForm,
    authMode,
    setAuthMode,
    captcha,
    setCaptcha,
    lockedUntil,
    session,
    setSession,
    capabilities,
    activeScreen,
    setActiveScreen,
    status,
    setStatus,
    isRefreshing,
    lastRefreshAt,
    trips: trips.trips,
    tripBookings: trips.tripBookings,
    myBookings: trips.myBookings,
    bookingTimeline: trips.bookingTimeline,
    selectedTripId: trips.selectedTripId,
    setSelectedTripId: trips.setSelectedTripId,
    fareForm: trips.fareForm,
    setFareForm: trips.setFareForm,
    tripForm: trips.tripForm,
    setTripForm: trips.setTripForm,
    tripFormError: trips.tripFormError,
    tripVersions: trips.tripVersions,
    tripDiffLabels: trips.tripDiffLabels,
    warehouses: operations.warehouses,
    zones: operations.zones,
    locations: operations.locations,
    partners: operations.partners,
    warehouseForm: operations.warehouseForm,
    setWarehouseForm: operations.setWarehouseForm,
    zoneForm: operations.zoneForm,
    setZoneForm: operations.setZoneForm,
    locationForm: operations.locationForm,
    setLocationForm: operations.setLocationForm,
    partnerForm: operations.partnerForm,
    setPartnerForm: operations.setPartnerForm,
    plans: operations.plans,
    inventoryTasks: operations.inventoryTasks,
    inventoryLines: operations.inventoryLines,
    planForm: operations.planForm,
    setPlanForm: operations.setPlanForm,
    taskForm: operations.taskForm,
    setTaskForm: operations.setTaskForm,
    lineForm: operations.lineForm,
    setLineForm: operations.setLineForm,
    correctiveForm: operations.correctiveForm,
    setCorrectiveForm: operations.setCorrectiveForm,
    variancePreview: operations.variancePreview,
    alerts: operations.alerts,
    jobs: jobs.jobs,
    selectedJobId: jobs.selectedJobId,
    setSelectedJobId: jobs.setSelectedJobId,
    rowErrors: jobs.rowErrors,
    jobForm: jobs.jobForm,
    setJobForm: jobs.setJobForm,
    dedupeForm: jobs.dedupeForm,
    setDedupeForm: jobs.setDedupeForm,
    dedupeResult: jobs.dedupeResult,
    verificationRequests: operations.verificationRequests,
    verificationComment: operations.verificationComment,
    setVerificationComment: operations.setVerificationComment,
    verificationRequestForm: operations.verificationRequestForm,
    setVerificationRequestForm: operations.setVerificationRequestForm,
    documentForm: operations.documentForm,
    setDocumentForm: operations.setDocumentForm,
    verificationOpenResult: operations.verificationOpenResult,
    operationsError: operations.operationsError,
    favorites: profile.favorites,
    comparisons: profile.comparisons,
    preference: profile.preference,
    travelerProfiles: profile.travelerProfiles,
    travelerReveal: profile.travelerReveal,
    exportRequests: profile.exportRequests,
    profileError: profile.profileError,
    profileForms: profile.profileForms,
    setProfileForms: profile.setProfileForms,
    canRequestUnmasked: profile.canRequestUnmasked,
    refreshData,
    handleLogin,
    handleRegister,
    handleChangePassword,
    handleLogout,
    toneVariant,
    statusVariant,
    handlePublish: trips.handlePublish,
    handleTripSubmit: trips.handleTripSubmit,
    startTripEdit: trips.startTripEdit,
    handleFareEstimate: trips.handleFareEstimate,
    handleBookingAction: trips.handleBookingAction,
    handleCreateJob: jobs.handleCreateJob,
    handleRetryJob: jobs.handleRetryJob,
    handleResolveRowError: jobs.handleResolveRowError,
    handleDedupeCheck: jobs.handleDedupeCheck,
    handleVerificationReview: operations.handleVerificationReview,
    submitVerificationRequest: operations.submitVerificationRequest,
    uploadVerificationDocument: operations.uploadVerificationDocument,
    openVerificationDocument: operations.openVerificationDocument,
    createWarehouse: operations.createWarehouse,
    createZone: operations.createZone,
    createLocation: operations.createLocation,
    createPartner: operations.createPartner,
    createInventoryPlan: operations.createInventoryPlan,
    createInventoryTask: operations.createInventoryTask,
    createCountLine: operations.createCountLine,
    createCorrectiveAction: operations.createCorrectiveAction,
    approveCorrectiveAction: operations.approveCorrectiveAction,
    acknowledgeCorrectiveAction: operations.acknowledgeCorrectiveAction,
    closeVariance: operations.closeVariance,
    createFavorite: profile.createFavorite,
    deleteFavorite: profile.deleteFavorite,
    createComparison: profile.createComparison,
    deleteComparison: profile.deleteComparison,
    createReminder: profile.createReminder,
    acknowledgeReminder: profile.acknowledgeReminder,
    updatePreference: profile.updatePreference,
    saveTravelerProfile: profile.saveTravelerProfile,
    revealTravelerField: profile.revealTravelerField,
    requestExport: profile.requestExport,
    submitDeletionRequest: profile.submitDeletionRequest,
  };
}
