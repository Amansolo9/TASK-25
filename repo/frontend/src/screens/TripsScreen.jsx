import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";

export function TripsScreen({
  renderCards,
  trips,
  statusVariant,
  handlePublish,
  handleTripSubmit = (event) => event.preventDefault(),
  tripForm = {
    title: "",
    origin: "",
    destination: "",
    service_date: "",
    pickup_window_start: "",
    pickup_window_end: "",
    signup_deadline: "",
    capacity_limit: 4,
    pricing_model: "flat",
    fare_cents: 0,
    tax_bps: 0,
    fee_cents: 0,
    cancellation_cutoff_minutes: 60,
    waypoints_text: "",
  },
  setTripForm = () => {},
  tripFormError = "",
  tripVersions = [],
  tripDiffLabels = [],
  startTripEdit = () => {},
  setSelectedTripId,
  fareForm,
  setFareForm,
  handleFareEstimate,
  myBookings,
  tripBookings,
  handleBookingAction,
  selectedTripId,
  bookingTimeline,
  canManageTrips = false,
}) {
  const bookingItems = [
    ...myBookings,
    ...tripBookings.filter((tripBooking) => !myBookings.some((my) => my.id === tripBooking.id)),
  ];

  return (
    <>
      {canManageTrips ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Trip Authoring</CardTitle>
            <CardDescription>Create or edit trips with explicit signup deadline checks.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <form className="grid gap-3 md:grid-cols-2" onSubmit={handleTripSubmit}>
              <Input value={tripForm.title} onChange={(e) => setTripForm((p) => ({ ...p, title: e.target.value }))} placeholder="Trip title" />
              <Input value={tripForm.service_date} onChange={(e) => setTripForm((p) => ({ ...p, service_date: e.target.value }))} placeholder="Service date (YYYY-MM-DD)" />
              <Input value={tripForm.origin} onChange={(e) => setTripForm((p) => ({ ...p, origin: e.target.value }))} placeholder="Origin" />
              <Input value={tripForm.destination} onChange={(e) => setTripForm((p) => ({ ...p, destination: e.target.value }))} placeholder="Destination" />
              <Input value={tripForm.pickup_window_start} onChange={(e) => setTripForm((p) => ({ ...p, pickup_window_start: e.target.value }))} placeholder="Pickup window start (ISO)" />
              <Input value={tripForm.pickup_window_end} onChange={(e) => setTripForm((p) => ({ ...p, pickup_window_end: e.target.value }))} placeholder="Pickup window end (ISO)" />
              <Input value={tripForm.signup_deadline} onChange={(e) => setTripForm((p) => ({ ...p, signup_deadline: e.target.value }))} placeholder="Signup deadline (ISO)" />
              <Input type="number" value={tripForm.capacity_limit} onChange={(e) => setTripForm((p) => ({ ...p, capacity_limit: e.target.value }))} placeholder="Capacity" />
              <Input value={tripForm.pricing_model} onChange={(e) => setTripForm((p) => ({ ...p, pricing_model: e.target.value }))} placeholder="Pricing model" />
              <Input type="number" value={tripForm.fare_cents} onChange={(e) => setTripForm((p) => ({ ...p, fare_cents: e.target.value }))} placeholder="Fare cents" />
              <Input type="number" value={tripForm.tax_bps} onChange={(e) => setTripForm((p) => ({ ...p, tax_bps: e.target.value }))} placeholder="Tax bps" />
              <Input type="number" value={tripForm.fee_cents} onChange={(e) => setTripForm((p) => ({ ...p, fee_cents: e.target.value }))} placeholder="Fee cents" />
              <Input type="number" value={tripForm.cancellation_cutoff_minutes} onChange={(e) => setTripForm((p) => ({ ...p, cancellation_cutoff_minutes: e.target.value }))} placeholder="Cancellation cutoff minutes" />
              <textarea
                className="min-h-20 rounded-md border bg-background p-3 text-sm md:col-span-2"
                value={tripForm.waypoints_text}
                onChange={(e) => setTripForm((p) => ({ ...p, waypoints_text: e.target.value }))}
                placeholder="Waypoints (one per line: name|address)"
              />
              <Button className="md:col-span-2">Save Trip</Button>
            </form>
            {tripFormError && <p className="text-xs text-rose-700">{tripFormError}</p>}
          </CardContent>
        </Card>
      ) : (
        <Card className="border-amber-300 bg-amber-50/70">
          <CardContent className="p-4 text-sm text-amber-800">
            Not authorized for trip authoring. You can still book, track, and acknowledge trip updates.
          </CardContent>
        </Card>
      )}

      {renderCards(
        trips,
        (trip) => (
          <Card key={trip.id}>
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-3">
                <CardTitle className="text-base">{trip.title}</CardTitle>
                <Badge variant={statusVariant(trip.status)}>{trip.status}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>{trip.origin} to {trip.destination}</p>
              <p>Version {trip.current_version} | Capacity {trip.capacity_limit}</p>
              <div className="flex flex-wrap gap-2">
                {canManageTrips && (
                  <>
                    <Button size="sm" variant="secondary" onClick={() => handlePublish(trip.id, "publish")}>Publish</Button>
                    <Button size="sm" variant="secondary" onClick={() => handlePublish(trip.id, "unpublish")}>Unpublish</Button>
                    <Button size="sm" variant="ghost" onClick={() => startTripEdit(trip)}>Edit + Version</Button>
                  </>
                )}
                <Button size="sm" variant="ghost" onClick={() => setSelectedTripId(String(trip.id))}>View bookings</Button>
              </div>
            </CardContent>
          </Card>
        ),
        "No trips available for this tenant yet."
      )}

      {!!tripDiffLabels.length && (
        <Card className="border-amber-300 bg-amber-50/70">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Material Update Impact</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-amber-900">
            <p>Existing riders must acknowledge the latest trip version before cancellation/refund actions.</p>
            <div className="flex flex-wrap gap-2">
              {tripDiffLabels.map((label) => (
                <Badge key={label} variant="warning">{label}</Badge>
              ))}
            </div>
            {!!tripVersions.length && <p>Latest version: {tripVersions[0]?.version_number || "n/a"}</p>}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Fare Estimator</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 sm:grid-cols-[1fr_120px_auto]" onSubmit={handleFareEstimate}>
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={fareForm.trip_id}
              onChange={(event) => setFareForm((prev) => ({ ...prev, trip_id: event.target.value }))}
              aria-label="Trip for fare estimate"
            >
              <option value="">Select trip</option>
              {trips.map((trip) => (
                <option key={trip.id} value={trip.id}>{trip.title}</option>
              ))}
            </select>
            <Input
              type="number"
              min={1}
              value={fareForm.seats}
              onChange={(event) => setFareForm((prev) => ({ ...prev, seats: Number(event.target.value) || 1 }))}
              aria-label="Seats for fare estimate"
            />
            <Button disabled={!fareForm.trip_id}>Estimate</Button>
          </form>
          {fareForm.total_cents !== null && (
            <p className="mt-3 text-sm text-muted-foreground">Estimated total: {fareForm.total_cents} cents</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Booking Actions</CardTitle>
          <CardDescription>Cancel, request refunds, review timelines, and process no-show decisions.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">Selected trip: {selectedTripId || "None"}</p>
          {renderCards(
            bookingItems,
            (booking) => (
              <Card key={booking.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-3">
                    <CardTitle className="text-sm">Booking #{booking.id}</CardTitle>
                    <Badge variant={statusVariant(booking.status)}>{booking.status}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2 text-xs text-muted-foreground">
                  <p>Trip {booking.trip} | Re-ack required: {booking.reack_required ? "yes" : "no"}</p>
                  {booking.reack_required ? (
                    <p className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-amber-800">
                      New version available. Rider acknowledgment is required before cancel or refund actions.
                    </p>
                  ) : (
                    <p className="text-emerald-700">Version acknowledged. Rider actions are unlocked.</p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="ghost" onClick={() => handleBookingAction("timeline", booking.id)}>Timeline</Button>
                    <Button size="sm" variant="secondary" onClick={() => handleBookingAction("acknowledge", booking.id, {})} disabled={!booking.reack_required}>Acknowledge Update</Button>
                    <Button size="sm" variant="secondary" onClick={() => handleBookingAction("cancel", booking.id, { reason: "Cancelled from dashboard" })} disabled={booking.reack_required}>Cancel</Button>
                    <Button size="sm" variant="secondary" onClick={() => handleBookingAction("refundRequest", booking.id, { reason: "Refund requested from dashboard" })} disabled={booking.reack_required}>Refund Request</Button>
                    <Button size="sm" variant="secondary" onClick={() => handleBookingAction("noShow", booking.id, { reason: "Marked by operations" })}>No-show</Button>
                    <Button size="sm" variant="secondary" onClick={() => handleBookingAction("refundDecision", booking.id, { decision: "approved" })}>Approve Refund</Button>
                  </div>
                </CardContent>
              </Card>
            ),
            "No bookings available for this user or selected trip."
          )}

          {!!bookingTimeline.length && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Latest Timeline</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-xs text-muted-foreground">
                {bookingTimeline.map((event) => (
                  <p key={event.id}>{event.from_status || "new"} {"->"} {event.to_status} ({event.reason})</p>
                ))}
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>
    </>
  );
}
