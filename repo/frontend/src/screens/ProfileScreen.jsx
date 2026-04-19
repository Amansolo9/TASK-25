import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";

export function ProfileScreen({
  profileForms,
  setProfileForms,
  preference,
  updatePreference,
  createFavorite,
  favorites,
  deleteFavorite,
  createComparison,
  comparisons,
  deleteComparison,
  createReminder,
  alerts,
  acknowledgeReminder,
  travelerProfiles,
  saveTravelerProfile,
  revealTravelerField,
  travelerReveal,
  canRequestUnmasked,
  exportRequests,
  requestExport,
  submitDeletionRequest,
  profileError,
}) {
  const hasRevealModal = profileForms.revealTargetProfileId && profileForms.revealTargetField;

  return (
    <>
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Preferences</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm">
          <form className="grid gap-3 md:grid-cols-2" onSubmit={updatePreference}>
            <Input value={profileForms.prefLocale} onChange={(event) => setProfileForms((prev) => ({ ...prev, prefLocale: event.target.value }))} placeholder="Locale" />
            <Input value={profileForms.prefTimezone} onChange={(event) => setProfileForms((prev) => ({ ...prev, prefTimezone: event.target.value }))} placeholder="Timezone" />
            <label className="flex items-center gap-2"><input type="checkbox" checked={Boolean(profileForms.prefLargeText)} onChange={(event) => setProfileForms((prev) => ({ ...prev, prefLargeText: event.target.checked }))} />Large text mode</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={Boolean(profileForms.prefHighContrast)} onChange={(event) => setProfileForms((prev) => ({ ...prev, prefHighContrast: event.target.checked }))} />High contrast mode</label>
            <Button className="md:col-span-2">Save Preferences</Button>
          </form>
          {preference?.updated_at && <p className="text-xs text-muted-foreground">Last updated {new Date(preference.updated_at).toLocaleString()}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Traveler Profiles</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <form className="grid gap-3 md:grid-cols-2" onSubmit={saveTravelerProfile}>
            <Input value={profileForms.travelerDisplayName} onChange={(event) => setProfileForms((prev) => ({ ...prev, travelerDisplayName: event.target.value }))} placeholder="Display name" />
            <Input value={profileForms.travelerIdentifier} onChange={(event) => setProfileForms((prev) => ({ ...prev, travelerIdentifier: event.target.value }))} placeholder="Traveler identifier" />
            <Input value={profileForms.travelerGovernmentId} onChange={(event) => setProfileForms((prev) => ({ ...prev, travelerGovernmentId: event.target.value }))} placeholder="Government ID" />
            <Input value={profileForms.travelerCredentialNumber} onChange={(event) => setProfileForms((prev) => ({ ...prev, travelerCredentialNumber: event.target.value }))} placeholder="Credential number" />
            <Button disabled={!profileForms.travelerDisplayName} className="md:col-span-2">Save Traveler Profile</Button>
          </form>
          {travelerProfiles.map((item) => (
            <div key={item.id} className="space-y-2 rounded-md border p-3 text-sm">
              <p className="font-medium">{item.display_name}</p>
              <p>Traveler ID: {item.masked_identifier || "Not set"}</p>
              <p>Government ID: {item.masked_government_id || "Not set"}</p>
              <p>Credential #: {item.masked_credential_number || "Not set"}</p>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="secondary" onClick={() => setProfileForms((prev) => ({ ...prev, revealTargetProfileId: String(item.id), revealTargetField: "identifier" }))}>Reveal Identifier</Button>
                <Button size="sm" variant="secondary" onClick={() => setProfileForms((prev) => ({ ...prev, revealTargetProfileId: String(item.id), revealTargetField: "government-id" }))}>Reveal Government ID</Button>
                <Button size="sm" variant="secondary" onClick={() => setProfileForms((prev) => ({ ...prev, revealTargetProfileId: String(item.id), revealTargetField: "credential-number" }))}>Reveal Credential #</Button>
              </div>
              {travelerReveal[item.id] && <p className="text-xs text-muted-foreground">Revealed: {travelerReveal[item.id]}</p>}
            </div>
          ))}
          {!travelerProfiles.length && <p className="text-sm text-muted-foreground">No traveler profiles yet.</p>}
        </CardContent>
      </Card>

      {hasRevealModal && (
        <Card className="border-amber-300 bg-amber-50/70">
          <CardHeader className="pb-2"><CardTitle className="text-base">Unmask Reason Required</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Input
              value={profileForms.revealReason}
              onChange={(event) => setProfileForms((prev) => ({ ...prev, revealReason: event.target.value }))}
              placeholder="Reason for revealing this field"
            />
            <div className="flex gap-2">
              <Button
                onClick={() =>
                  revealTravelerField(
                    Number(profileForms.revealTargetProfileId),
                    profileForms.revealTargetField,
                    profileForms.revealReason
                  )
                }
              >
                Confirm Reveal
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() =>
                  setProfileForms((prev) => ({
                    ...prev,
                    revealReason: "",
                    revealTargetProfileId: "",
                    revealTargetField: "identifier",
                  }))
                }
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Data Export</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <form className="grid gap-3 md:grid-cols-2" onSubmit={requestExport}>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={Boolean(profileForms.exportIncludeUnmasked)} onChange={(event) => setProfileForms((prev) => ({ ...prev, exportIncludeUnmasked: event.target.checked }))} />
              Include unmasked data
            </label>
            <Input value={profileForms.exportFormat} onChange={(event) => setProfileForms((prev) => ({ ...prev, exportFormat: event.target.value }))} placeholder="Export format" />
            <Input value={profileForms.exportJustification} onChange={(event) => setProfileForms((prev) => ({ ...prev, exportJustification: event.target.value }))} placeholder="Justification for unmasked export" className="md:col-span-2" />
            <Button disabled={Boolean(profileForms.exportIncludeUnmasked) && !canRequestUnmasked} className="md:col-span-2">Request Export</Button>
          </form>
          {!canRequestUnmasked && <p className="text-xs text-amber-700">Your role can request masked exports only. Unmasked exports require elevated permission.</p>}
          {exportRequests.map((item) => <div key={item.id} className="rounded-md border p-3 text-sm"><p>Status: {item.status}</p><p>Mode: {item.include_unmasked ? "unmasked" : "masked"}</p><p>Format: {item.format}</p></div>)}
          {!exportRequests.length && <p className="text-sm text-muted-foreground">No export requests yet.</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Account Deletion</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-muted-foreground">Deletion requests deactivate your account immediately. Retention and legal hold windows still apply to operational records.</p>
          <form className="grid gap-3" onSubmit={submitDeletionRequest}>
            <textarea className="min-h-20 w-full rounded-md border bg-background p-3 text-sm" value={profileForms.deletionRetentionNotice} onChange={(event) => setProfileForms((prev) => ({ ...prev, deletionRetentionNotice: event.target.value }))} placeholder="Acknowledge retention notice" />
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={Boolean(profileForms.retentionAcknowledged)} onChange={(event) => setProfileForms((prev) => ({ ...prev, retentionAcknowledged: event.target.checked }))} />
              I acknowledge retention and legal hold notices.
            </label>
            <Button variant="destructive" disabled={!profileForms.deletionRetentionNotice || !profileForms.retentionAcknowledged}>Request Account Deletion</Button>
          </form>
        </CardContent>
      </Card>

      {profileError && <Card className="border-rose-200 bg-rose-50/80"><CardContent className="p-4 text-sm text-rose-700">{profileError}</CardContent></Card>}

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Favorites</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <form className="grid gap-3 md:grid-cols-3" onSubmit={createFavorite}>
            <select className="h-10 rounded-md border bg-background px-3 text-sm" value={profileForms.favoriteKind} onChange={(event) => setProfileForms((prev) => ({ ...prev, favoriteKind: event.target.value }))}><option value="trip">trip</option><option value="profile">profile</option><option value="warehouse">warehouse</option></select>
            <Input value={profileForms.favoriteRef} onChange={(event) => setProfileForms((prev) => ({ ...prev, favoriteRef: event.target.value }))} placeholder="reference id" />
            <Button disabled={!profileForms.favoriteRef}>Add Favorite</Button>
          </form>
          {favorites.map((item) => <div key={item.id} className="flex items-center justify-between rounded-md border p-3 text-sm"><p>{item.kind}: {item.reference_id}</p><Button size="sm" variant="ghost" onClick={() => deleteFavorite(item.id)}>Remove</Button></div>)}
          {!favorites.length && <p className="text-sm text-muted-foreground">No saved favorites.</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Comparisons</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <form className="grid gap-3 md:grid-cols-3" onSubmit={createComparison}>
            <select className="h-10 rounded-md border bg-background px-3 text-sm" value={profileForms.comparisonKind} onChange={(event) => setProfileForms((prev) => ({ ...prev, comparisonKind: event.target.value }))}><option value="plan">plan</option><option value="trip">trip</option><option value="partner">partner</option></select>
            <Input value={profileForms.comparisonRef} onChange={(event) => setProfileForms((prev) => ({ ...prev, comparisonRef: event.target.value }))} placeholder="reference id" />
            <Button disabled={!profileForms.comparisonRef}>Add Comparison</Button>
          </form>
          {comparisons.map((item) => <div key={item.id} className="flex items-center justify-between rounded-md border p-3 text-sm"><p>{item.kind}: {item.reference_id}</p><Button size="sm" variant="ghost" onClick={() => deleteComparison(item.id)}>Remove</Button></div>)}
          {!comparisons.length && <p className="text-sm text-muted-foreground">No comparison items yet.</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Local Reminders</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <form className="grid gap-3" onSubmit={createReminder}>
            <Input value={profileForms.reminderTitle} onChange={(event) => setProfileForms((prev) => ({ ...prev, reminderTitle: event.target.value }))} placeholder="Reminder title" />
            <textarea className="min-h-20 w-full rounded-md border bg-background p-3 text-sm" value={profileForms.reminderMessage} onChange={(event) => setProfileForms((prev) => ({ ...prev, reminderMessage: event.target.value }))} placeholder="Reminder details" />
            <Button disabled={!profileForms.reminderTitle || !profileForms.reminderMessage}>Create Reminder</Button>
          </form>
          {alerts.map((alert) => (
            <div key={alert.id} className="flex items-center justify-between rounded-md border p-3 text-sm">
              <p>{alert.title} - {alert.message}</p>
              {alert.acknowledged ? <Badge variant="success">Acknowledged</Badge> : <Button size="sm" variant="secondary" onClick={() => acknowledgeReminder(alert.id)}>Acknowledge</Button>}
            </div>
          ))}
          {!alerts.length && <p className="text-sm text-muted-foreground">No reminders created yet.</p>}
        </CardContent>
      </Card>
    </>
  );
}
