import {
  AlertTriangle,
  Boxes,
  Bus,
  ClipboardCheck,
  Database,
  RefreshCw,
  Shield,
  UserRound,
} from "lucide-react";

import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { canAccessScreen, canPerform } from "./hooks/domains/accessDomain";
import { useAppController } from "./hooks/useAppController";
import { useWorkspaceScreens } from "./hooks/useWorkspaceScreens";
import { JobsScreen } from "./screens/JobsScreen";
import { InventoryScreen } from "./screens/InventoryScreen";
import { ProfileScreen } from "./screens/ProfileScreen";
import { TripsScreen } from "./screens/TripsScreen";
import { VerificationScreen } from "./screens/VerificationScreen";
import { WarehouseScreen } from "./screens/WarehouseScreen";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://localhost:8443";

const roleScreens = {
  senior: ["Trips", "Bookings", "Profile"],
  family_member: ["Trips", "Bookings", "Tracking", "Profile"],
  caregiver: ["Trips", "Trip Publishing", "Rider Support"],
  org_admin: ["Trips", "Warehouse", "Inventory", "Jobs", "Verification", "Audit", "Anomalies", "Profile"],
  platform_admin: ["Cross-Org Oversight", "Audit", "Anomalies", "Jobs", "Security", "Profile"],
};

const screenIcons = {
  Trips: Bus,
  Warehouse: Boxes,
  Inventory: ClipboardCheck,
  Jobs: Database,
  Verification: Shield,
  Audit: ClipboardCheck,
  "Cross-Org Oversight": RefreshCw,
  Anomalies: AlertTriangle,
  Security: Shield,
  Profile: UserRound,
};

const screenDescriptions = {
  Trips: "Manage routes, fare estimates, booking lifecycle events, and refund requests.",
  Warehouse: "View offline warehouse footprint, active facilities, and capacity anchors.",
  Inventory: "Track count plans and variance closure status by location and asset type.",
  Jobs: "Create and retry ingestion jobs, resolve row errors, and run dedupe checks.",
  Verification: "Review identity verification requests and submit approval decisions.",
  Audit: "Review operational change signals, mutation footprints, and unresolved ingest exceptions.",
  "Cross-Org Oversight": "Track high-level organization posture and cross-domain operational readiness.",
  Anomalies: "Review security and operations alerts that require administrative attention.",
  Security: "Monitor replay protection posture, signed mutation controls, and sensitive data access state.",
  Profile: "Manage preferences, traveler privacy data, exports, deletion requests, favorites, and reminders.",
};

function App() {
  const {
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
    capabilities,
    activeScreen,
    setActiveScreen,
    status,
    isRefreshing,
    lastRefreshAt,
    trips,
    tripBookings,
    myBookings,
    bookingTimeline,
    selectedTripId,
    setSelectedTripId,
    tripForm,
    setTripForm,
    tripFormError,
    tripVersions,
    tripDiffLabels,
    warehouses,
    zones,
    locations,
    partners,
    warehouseForm,
    setWarehouseForm,
    zoneForm,
    setZoneForm,
    locationForm,
    setLocationForm,
    partnerForm,
    setPartnerForm,
    plans,
    inventoryTasks,
    inventoryLines,
    planForm,
    setPlanForm,
    taskForm,
    setTaskForm,
    lineForm,
    setLineForm,
    correctiveForm,
    setCorrectiveForm,
    variancePreview,
    alerts,
    jobs,
    selectedJobId,
    setSelectedJobId,
    rowErrors,
    jobForm,
    setJobForm,
    dedupeForm,
    setDedupeForm,
    dedupeResult,
    verificationRequests,
    verificationComment,
    setVerificationComment,
    verificationRequestForm,
    setVerificationRequestForm,
    documentForm,
    setDocumentForm,
    verificationOpenResult,
    operationsError,
    favorites,
    comparisons,
    preference,
    travelerProfiles,
    travelerReveal,
    exportRequests,
    profileError,
    profileForms,
    setProfileForms,
    fareForm,
    setFareForm,
    canRequestUnmasked,
    refreshData,
    handleLogin,
    handleRegister,
    handleChangePassword,
    handleLogout,
    toneVariant,
    statusVariant,
    handlePublish,
    handleTripSubmit,
    startTripEdit,
    handleFareEstimate,
    handleBookingAction,
    handleCreateJob,
    handleRetryJob,
    handleResolveRowError,
    handleDedupeCheck,
    handleVerificationReview,
    submitVerificationRequest,
    uploadVerificationDocument,
    openVerificationDocument,
    createWarehouse,
    createZone,
    createLocation,
    createPartner,
    createInventoryPlan,
    createInventoryTask,
    createCountLine,
    createCorrectiveAction,
    approveCorrectiveAction,
    acknowledgeCorrectiveAction,
    closeVariance,
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
  } = useAppController({ apiBaseUrl: API_BASE_URL, roleScreens });

  const { allScreens, roleLabel, quickStats } = useWorkspaceScreens({
    sessionRoles: session.roles,
    roleScreens,
      statsByScreen: {
        Trips: trips.length,
        Warehouse: warehouses.length,
        Inventory: plans.length,
        Jobs: jobs.length,
        Verification: verificationRequests.length,
        Audit: rowErrors.length,
        "Cross-Org Oversight": session.roles.length,
        Anomalies: alerts.length,
        Security: travelerProfiles.length,
        Profile: favorites.length + travelerProfiles.length,
      },
    });
  const activeStat = quickStats.find((item) => item.screen === activeScreen);

  const canSeeActiveScreen = canAccessScreen(capabilities, activeScreen);

  function renderCards(items, renderer, emptyText) {
    if (!items.length) {
      return (
        <Card className="border-dashed">
          <CardContent className="flex items-center gap-3 p-6 text-sm text-muted-foreground">
            <AlertTriangle className="h-4 w-4 text-amber-600" aria-hidden="true" />
            <span>{emptyText}</span>
          </CardContent>
        </Card>
      );
    }
    return (
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item, index) => (
          <div key={item.id || `${index}`} className="reveal" style={{ animationDelay: `${index * 35}ms` }}>
            {renderer(item, index)}
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <a href="#app-main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-card focus:px-3 focus:py-2">
        Skip to main content
      </a>
      <div className="container py-4 md:py-6">
        <Card className="border shadow-xl">
          <header>
            <CardHeader className="space-y-4 border-b bg-gradient-to-r from-teal-50 via-white to-sky-50">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="space-y-1">
                  <CardTitle className="text-xl md:text-2xl">HarborOps Offline Transit & Logistics</CardTitle>
                  <CardDescription>
                    Senior-care transportation, warehouse, and inventory workflows on your local network.
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2" aria-live="polite">
                  <Badge variant={toneVariant(status.tone)}>{status.message}</Badge>
                  {session.me && (
                    <>
                      <Button variant="secondary" size="sm" onClick={refreshData} disabled={isRefreshing}>
                        <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} aria-hidden="true" />
                        {isRefreshing ? "Refreshing..." : "Refresh"}
                      </Button>
                      <Button variant="destructive" size="sm" onClick={handleLogout}>
                        Sign Out
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </CardHeader>
          </header>

          <CardContent className="p-4 md:p-6" id="app-main">
            {session.me && status.tone === "danger" && (
              <Card className="mb-4 border-rose-200 bg-rose-50/80">
                <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-sm text-rose-800">{status.message}</p>
                  <Button variant="secondary" size="sm" onClick={refreshData}>Retry load</Button>
                </CardContent>
              </Card>
            )}

            {!session.me && (
              <div className="grid gap-4 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Welcome</CardTitle>
                    <CardDescription>
                      Log in to access role-specific workflows for trips, inventory, warehouse, and jobs.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <div className="rounded-md border bg-muted/40 p-3">
                      <p className="font-medium">Demo Accounts</p>
                      <p>Org Admin: orgadmin / SecurePass1234</p>
                      <p>Senior: senior1 / SecurePass1234</p>
                    </div>
                    <p className="text-muted-foreground">
                      Authentication uses CSRF-protected session login and offline credential controls.
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Account Access</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex gap-2">
                      <Button type="button" variant={authMode === "login" ? "default" : "ghost"} onClick={() => setAuthMode("login")}>Login</Button>
                      <Button type="button" variant={authMode === "register" ? "default" : "ghost"} onClick={() => setAuthMode("register")}>Register</Button>
                      <Button type="button" variant={authMode === "password" ? "default" : "ghost"} onClick={() => setAuthMode("password")}>Change Password</Button>
                    </div>

                    {authMode === "login" && (
                      <form className="space-y-4" onSubmit={handleLogin} aria-label="Sign in form">
                        <div className="space-y-2">
                          <label className="text-sm font-medium" htmlFor="username">
                            Username
                          </label>
                          <Input
                            id="username"
                            value={auth.username}
                            autoComplete="username"
                            onChange={(event) => setAuth({ ...auth, username: event.target.value })}
                          />
                        </div>
                        <div className="space-y-2">
                          <label className="text-sm font-medium" htmlFor="password">
                            Password
                          </label>
                          <Input
                            id="password"
                            type="password"
                            value={auth.password}
                            autoComplete="current-password"
                            onChange={(event) => setAuth({ ...auth, password: event.target.value })}
                          />
                        </div>
                        {captcha.required && (
                          <div className="space-y-2 rounded-md border p-3 text-sm">
                            <p className="font-medium">CAPTCHA challenge</p>
                            <p>{captcha.prompt}</p>
                            <Input
                              value={captcha.response}
                              onChange={(event) => setCaptcha((prev) => ({ ...prev, response: event.target.value }))}
                              placeholder="CAPTCHA answer"
                              aria-label="CAPTCHA answer"
                            />
                          </div>
                        )}
                        {lockedUntil && (
                          <p className="text-xs text-amber-700">
                            Account locked until {new Date(lockedUntil).toLocaleString()}.
                          </p>
                        )}
                        <Button disabled={status.loading} className="w-full">
                          {status.loading ? "Signing in..." : "Sign In"}
                        </Button>
                      </form>
                    )}

                    {authMode === "register" && (
                      <form className="space-y-4" onSubmit={handleRegister} aria-label="Registration form">
                        <Input
                          value={registerForm.organization_code}
                          onChange={(event) => setRegisterForm((prev) => ({ ...prev, organization_code: event.target.value }))}
                          placeholder="Organization code"
                          aria-label="Organization code"
                        />
                        <Input
                          value={registerForm.real_name}
                          onChange={(event) => setRegisterForm((prev) => ({ ...prev, real_name: event.target.value }))}
                          placeholder="Real name"
                          aria-label="Real name"
                        />
                        <Input
                          value={registerForm.username}
                          onChange={(event) => setRegisterForm((prev) => ({ ...prev, username: event.target.value }))}
                          placeholder="Username"
                          aria-label="Registration username"
                        />
                        <Input
                          type="password"
                          value={registerForm.password}
                          onChange={(event) => setRegisterForm((prev) => ({ ...prev, password: event.target.value }))}
                          placeholder="Password"
                          aria-label="Registration password"
                        />
                        <p className="text-xs text-muted-foreground">{registrationPasswordPolicy}</p>
                        <Button disabled={status.loading} className="w-full">Create Account</Button>
                      </form>
                    )}

                    {authMode === "password" && (
                      <form className="space-y-4" onSubmit={handleChangePassword} aria-label="Change password form">
                        <Input
                          type="password"
                          value={changePasswordForm.current_password}
                          onChange={(event) =>
                            setChangePasswordForm((prev) => ({ ...prev, current_password: event.target.value }))
                          }
                          placeholder="Current password"
                          aria-label="Current password"
                        />
                        <Input
                          type="password"
                          value={changePasswordForm.new_password}
                          onChange={(event) =>
                            setChangePasswordForm((prev) => ({ ...prev, new_password: event.target.value }))
                          }
                          placeholder="New password"
                          aria-label="New password"
                        />
                        <Button disabled={status.loading} className="w-full">Update Password</Button>
                      </form>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}

            {session.me && (
              <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
                <aside>
                  <Card className="h-fit glow-panel">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base">Operator Context</CardTitle>
                      <CardDescription>{session.me.real_name}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-1 text-sm">
                        <p className="font-medium">User</p>
                        <p className="text-muted-foreground">{session.me.username}</p>
                      </div>
                      <div className="space-y-1 text-sm">
                        <p className="font-medium">Roles</p>
                        <p className="text-muted-foreground">{roleLabel}</p>
                      </div>

                      <nav className="grid gap-2" aria-label="Workspace screens">
                        {allScreens.filter((screen) => canAccessScreen(capabilities, screen)).map((screen) => {
                          const Icon = screenIcons[screen] || Database;
                          const stat = quickStats.find((item) => item.screen === screen);
                          return (
                            <Button
                              key={screen}
                              variant={activeScreen === screen ? "default" : "ghost"}
                              className="justify-between"
                              onClick={() => setActiveScreen(screen)}
                              aria-current={activeScreen === screen ? "page" : undefined}
                            >
                              <span className="flex items-center gap-2">
                                <Icon className="h-4 w-4" aria-hidden="true" />
                                {screen}
                              </span>
                              {stat && <Badge variant="info">{stat.value}</Badge>}
                            </Button>
                          );
                        })}
                      </nav>
                    </CardContent>
                  </Card>
                </aside>

                <main className="space-y-4" aria-busy={isRefreshing}>
                  <Card className="glow-panel">
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between gap-3">
                        <CardTitle className="text-lg">{activeScreen}</CardTitle>
                        {activeStat && <Badge variant="info">{activeStat.value}</Badge>}
                      </div>
                      <CardDescription>
                        {screenDescriptions[activeScreen] || "This workspace is scaffolded for the next iteration."}
                      </CardDescription>
                      {lastRefreshAt && (
                        <p className="text-xs text-muted-foreground">Last synchronized {lastRefreshAt.toLocaleTimeString()}</p>
                      )}
                    </CardHeader>
                  </Card>

                  {!canSeeActiveScreen && (
                    <Card className="border-rose-200 bg-rose-50/80">
                      <CardContent className="p-6 text-sm text-rose-700">
                        Not authorized for this module. Your role does not include access to {activeScreen}.
                      </CardContent>
                    </Card>
                  )}

                  {canSeeActiveScreen && activeScreen === "Trips" && (
                    <TripsScreen
                      renderCards={renderCards}
                      trips={trips}
                      statusVariant={statusVariant}
                      handlePublish={handlePublish}
                      handleTripSubmit={handleTripSubmit}
                      tripForm={tripForm}
                      setTripForm={setTripForm}
                      tripFormError={tripFormError}
                      tripVersions={tripVersions}
                      tripDiffLabels={tripDiffLabels}
                      startTripEdit={startTripEdit}
                      setSelectedTripId={setSelectedTripId}
                      fareForm={fareForm}
                      setFareForm={setFareForm}
                      handleFareEstimate={handleFareEstimate}
                      myBookings={myBookings}
                      tripBookings={tripBookings}
                      handleBookingAction={handleBookingAction}
                      selectedTripId={selectedTripId}
                      bookingTimeline={bookingTimeline}
                      canManageTrips={canPerform(capabilities, "trip.manage")}
                    />
                  )}

                  {canSeeActiveScreen && activeScreen === "Jobs" && (
                    <JobsScreen
                      renderCards={renderCards}
                      jobForm={jobForm}
                      setJobForm={setJobForm}
                      handleCreateJob={handleCreateJob}
                      jobs={jobs}
                      handleRetryJob={handleRetryJob}
                      setSelectedJobId={setSelectedJobId}
                      selectedJobId={selectedJobId}
                      rowErrors={rowErrors}
                      handleResolveRowError={handleResolveRowError}
                      dedupeForm={dedupeForm}
                      setDedupeForm={setDedupeForm}
                      handleDedupeCheck={handleDedupeCheck}
                      dedupeResult={dedupeResult}
                      statusVariant={statusVariant}
                    />
                  )}

                  {canSeeActiveScreen && activeScreen === "Verification" && (
                    <VerificationScreen
                      renderCards={renderCards}
                      verificationComment={verificationComment}
                      setVerificationComment={setVerificationComment}
                      verificationRequests={verificationRequests}
                      statusVariant={statusVariant}
                      handleVerificationReview={handleVerificationReview}
                      submitVerificationRequest={submitVerificationRequest}
                      verificationRequestForm={verificationRequestForm}
                      setVerificationRequestForm={setVerificationRequestForm}
                      uploadVerificationDocument={uploadVerificationDocument}
                      documentForm={documentForm}
                      setDocumentForm={setDocumentForm}
                      openVerificationDocument={openVerificationDocument}
                      verificationOpenResult={verificationOpenResult}
                      operationsError={operationsError}
                      canReview={canPerform(capabilities, "verification.review")}
                    />
                  )}

                  {canSeeActiveScreen && activeScreen === "Warehouse" && (
                    <WarehouseScreen
                      renderCards={renderCards}
                      warehouses={warehouses}
                      zones={zones}
                      locations={locations}
                      partners={partners}
                      warehouseForm={warehouseForm}
                      setWarehouseForm={setWarehouseForm}
                      zoneForm={zoneForm}
                      setZoneForm={setZoneForm}
                      locationForm={locationForm}
                      setLocationForm={setLocationForm}
                      partnerForm={partnerForm}
                      setPartnerForm={setPartnerForm}
                      createWarehouse={createWarehouse}
                      createZone={createZone}
                      createLocation={createLocation}
                      createPartner={createPartner}
                      operationsError={operationsError}
                    />
                  )}

                  {canSeeActiveScreen && activeScreen === "Inventory" && (
                    <InventoryScreen
                      renderCards={renderCards}
                      plans={plans}
                      tasks={inventoryTasks}
                      lines={inventoryLines}
                      statusVariant={statusVariant}
                      planForm={planForm}
                      setPlanForm={setPlanForm}
                      taskForm={taskForm}
                      setTaskForm={setTaskForm}
                      lineForm={lineForm}
                      setLineForm={setLineForm}
                      correctiveForm={correctiveForm}
                      setCorrectiveForm={setCorrectiveForm}
                      variancePreview={variancePreview}
                      createInventoryPlan={createInventoryPlan}
                      createInventoryTask={createInventoryTask}
                      createCountLine={createCountLine}
                      createCorrectiveAction={createCorrectiveAction}
                      approveCorrectiveAction={approveCorrectiveAction}
                      acknowledgeCorrectiveAction={acknowledgeCorrectiveAction}
                      closeVariance={closeVariance}
                      locations={locations}
                      operationsError={operationsError}
                    />
                  )}

                  {canSeeActiveScreen && activeScreen === "Anomalies" &&
                    renderCards(
                      alerts,
                      (alert) => (
                        <Card key={alert.id}>
                          <CardHeader className="pb-2">
                            <div className="flex items-start justify-between gap-3">
                              <CardTitle className="text-base">{alert.title}</CardTitle>
                              <Badge variant={statusVariant(alert.severity)}>{alert.severity}</Badge>
                            </div>
                          </CardHeader>
                          <CardContent className="space-y-1 text-sm text-muted-foreground">
                            <p>{alert.details}</p>
                            <p>{alert.alert_type} | {alert.acknowledged ? "Acknowledged" : "Pending"}</p>
                          </CardContent>
                        </Card>
                      ),
                      "No anomaly alerts at this time."
                    )}

                  {canSeeActiveScreen && activeScreen === "Audit" && (
                    <div className="grid gap-3 lg:grid-cols-3">
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base">Job Throughput</CardTitle>
                          <CardDescription>Total tracked jobs in current scope</CardDescription>
                        </CardHeader>
                        <CardContent>
                          <p className="text-2xl font-semibold">{jobs.length}</p>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base">Failed Jobs</CardTitle>
                          <CardDescription>Jobs currently in failed status</CardDescription>
                        </CardHeader>
                        <CardContent>
                          <p className="text-2xl font-semibold">{jobs.filter((job) => job.status === "failed").length}</p>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base">Open Row Errors</CardTitle>
                          <CardDescription>Unresolved ingest row exceptions</CardDescription>
                        </CardHeader>
                        <CardContent>
                          <p className="text-2xl font-semibold">{rowErrors.filter((error) => !error.resolved).length}</p>
                        </CardContent>
                      </Card>
                    </div>
                  )}

                  {canSeeActiveScreen && activeScreen === "Cross-Org Oversight" && (
                    <div className="grid gap-3 lg:grid-cols-2">
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base">Organization Context</CardTitle>
                          <CardDescription>Active runtime organization context</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2 text-sm text-muted-foreground">
                          <p>Organization code: <span className="font-medium text-foreground">{session.user?.organization_code || "Unknown"}</span></p>
                          <p>Roles in session: <span className="font-medium text-foreground">{session.roles.join(", ") || "None"}</span></p>
                          <p>Signed mutation scope: <span className="font-medium text-foreground">/api/</span></p>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base">Operational Signals</CardTitle>
                          <CardDescription>Cross-domain counts in current scope</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2 text-sm text-muted-foreground">
                          <p>Trips: <span className="font-medium text-foreground">{trips.length}</span></p>
                          <p>Warehouses: <span className="font-medium text-foreground">{warehouses.length}</span></p>
                          <p>Pending alerts: <span className="font-medium text-foreground">{alerts.filter((alert) => !alert.acknowledged).length}</span></p>
                          <p>Verification requests: <span className="font-medium text-foreground">{verificationRequests.length}</span></p>
                        </CardContent>
                      </Card>
                    </div>
                  )}

                  {canSeeActiveScreen && activeScreen === "Security" && (
                    <div className="grid gap-3 lg:grid-cols-2">
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base">Replay Protection</CardTitle>
                          <CardDescription>Mutation replay controls currently enforced</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2 text-sm text-muted-foreground">
                          <p>Session mutations: nonce + timestamp replay checks</p>
                          <p>Machine mutations: HMAC signature + nonce + timestamp</p>
                          <p>Protected mutation prefix: <span className="font-medium text-foreground">/api/</span></p>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base">Sensitive Access Signals</CardTitle>
                          <CardDescription>High-sensitivity operations in session scope</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2 text-sm text-muted-foreground">
                          <p>Traveler profiles: <span className="font-medium text-foreground">{travelerProfiles.length}</span></p>
                          <p>Export requests: <span className="font-medium text-foreground">{exportRequests.length}</span></p>
                          <p>Recent reveal fields: <span className="font-medium text-foreground">{Object.keys(travelerReveal || {}).length}</span></p>
                        </CardContent>
                      </Card>
                    </div>
                  )}

                  {canSeeActiveScreen && activeScreen === "Profile" && (
                    <ProfileScreen
                      profileForms={profileForms}
                      setProfileForms={setProfileForms}
                      preference={preference}
                      updatePreference={updatePreference}
                      createFavorite={createFavorite}
                      favorites={favorites}
                      deleteFavorite={deleteFavorite}
                      createComparison={createComparison}
                      comparisons={comparisons}
                      deleteComparison={deleteComparison}
                      createReminder={createReminder}
                      alerts={alerts}
                      acknowledgeReminder={acknowledgeReminder}
                      travelerProfiles={travelerProfiles}
                      saveTravelerProfile={saveTravelerProfile}
                      revealTravelerField={revealTravelerField}
                      travelerReveal={travelerReveal}
                      canRequestUnmasked={canRequestUnmasked}
                      exportRequests={exportRequests}
                      requestExport={requestExport}
                      submitDeletionRequest={submitDeletionRequest}
                      profileError={profileError}
                    />
                  )}

                  {canSeeActiveScreen && !session.roles.includes("platform_admin") && !Object.keys(screenDescriptions).includes(activeScreen) && (
                    <Card>
                      <CardContent className="p-6 text-sm text-muted-foreground">
                        This section is available in navigation and is ready for its next UI pass.
                      </CardContent>
                    </Card>
                  )}
                </main>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default App;
