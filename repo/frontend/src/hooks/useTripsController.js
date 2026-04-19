import { useCallback, useEffect, useState } from "react";

import { bookingActionEndpoints } from "./domains/tripsDomain";

const initialFareForm = { trip_id: "", seats: 1, total_cents: null };
const initialTripForm = {
  title: "",
  origin: "",
  destination: "",
  service_date: "",
  pickup_window_start: "",
  pickup_window_end: "",
  timezone_id: "UTC",
  signup_deadline: "",
  capacity_limit: 4,
  pricing_model: "flat",
  fare_cents: 2500,
  tax_bps: 0,
  fee_cents: 0,
  cancellation_cutoff_minutes: 60,
  waypoints_text: "",
};

function parseWaypoints(waypointsText) {
  return String(waypointsText || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [name, address] = line.split("|").map((part) => part?.trim() || "");
      return { sequence: index + 1, name: name || `Stop ${index + 1}`, address: address || name || "" };
    });
}

function computeTripDiffLabels(previousVersion, currentVersion) {
  if (!previousVersion || !currentVersion) return [];
  const previous = previousVersion.snapshot_json || {};
  const current = currentVersion.snapshot_json || {};
  const labels = [];
  if (previous.pickup_window_start !== current.pickup_window_start) labels.push("Pickup window updated");
  if (previous.signup_deadline !== current.signup_deadline) labels.push("Signup deadline updated");
  if (previous.capacity_limit !== current.capacity_limit) labels.push("Capacity updated");
  if (previous.fare_cents !== current.fare_cents) labels.push("Pricing updated");
  if (previous.origin !== current.origin || previous.destination !== current.destination) {
    labels.push("Route endpoints updated");
  }
  return labels;
}

function validateSignupDeadline(form) {
  if (!form.pickup_window_start || !form.signup_deadline) {
    return "Pickup start and signup deadline are required.";
  }
  const pickupStart = new Date(form.pickup_window_start);
  const deadline = new Date(form.signup_deadline);
  const minHours = 2 * 60 * 60 * 1000;
  if (pickupStart.getTime() - deadline.getTime() < minHours) {
    return "Signup deadline must be at least 2 hours before pickup start.";
  }
  return "";
}

export function useTripsController({ api, setStatus }) {
  const [trips, setTrips] = useState([]);
  const [tripBookings, setTripBookings] = useState([]);
  const [myBookings, setMyBookings] = useState([]);
  const [bookingTimeline, setBookingTimeline] = useState([]);
  const [selectedTripId, setSelectedTripId] = useState("");
  const [fareForm, setFareForm] = useState(initialFareForm);
  const [tripForm, setTripForm] = useState(initialTripForm);
  const [tripFormError, setTripFormError] = useState("");
  const [tripVersions, setTripVersions] = useState([]);
  const [tripDiffLabels, setTripDiffLabels] = useState([]);

  const loadTripBookings = useCallback(
    async (tripId) => {
      if (!tripId) {
        setTripBookings([]);
        return;
      }
      try {
        const data = await api(`/api/trips/${tripId}/bookings/`);
        setTripBookings(data || []);
      } catch {
        setTripBookings([]);
      }
    },
    [api]
  );

  const loadTrips = useCallback(async () => {
    try {
      const data = await api("/api/trips/");
      setTrips(data || []);
      const firstTrip = (data || [])[0];
      if (firstTrip) {
        setSelectedTripId(String(firstTrip.id));
        setFareForm((prev) => ({ ...prev, trip_id: String(firstTrip.id) }));
      }
    } catch {
      setTrips([]);
    }
  }, [api]);

  const loadMyBookings = useCallback(async () => {
    try {
      const data = await api("/api/trips/bookings/mine/");
      setMyBookings(data || []);
    } catch {
      setMyBookings([]);
    }
  }, [api]);

  useEffect(() => {
    loadTripBookings(selectedTripId);
  }, [selectedTripId, loadTripBookings]);

  const loadTripVersions = useCallback(
    async (tripId) => {
      if (!tripId) {
        setTripVersions([]);
        setTripDiffLabels([]);
        return;
      }
      try {
        const data = await api(`/api/trips/${tripId}/versions/`);
        const versions = data || [];
        setTripVersions(versions);
        const latest = versions[0];
        const previous = versions[1];
        setTripDiffLabels(computeTripDiffLabels(previous, latest));
      } catch {
        setTripVersions([]);
        setTripDiffLabels([]);
      }
    },
    [api]
  );

  const handlePublish = useCallback(
    async (tripId, nextAction) => {
      try {
        await api(`/api/trips/${tripId}/${nextAction}/`, { method: "POST" }, true);
        await loadTrips();
        setStatus({ loading: false, message: `Trip ${nextAction} complete`, tone: "success" });
      } catch (error) {
        setStatus({ loading: false, message: error.message, tone: "danger" });
      }
    },
    [api, loadTrips, setStatus]
  );

  const handleTripSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      const validationMessage = validateSignupDeadline(tripForm);
      setTripFormError(validationMessage);
      if (validationMessage) {
        return;
      }
      try {
        const payload = {
          ...tripForm,
          capacity_limit: Number(tripForm.capacity_limit),
          fare_cents: Number(tripForm.fare_cents),
          tax_bps: Number(tripForm.tax_bps),
          fee_cents: Number(tripForm.fee_cents),
          cancellation_cutoff_minutes: Number(tripForm.cancellation_cutoff_minutes),
          waypoints: parseWaypoints(tripForm.waypoints_text),
        };
        if (selectedTripId) {
          await api(
            `/api/trips/${selectedTripId}/`,
            {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            },
            true
          );
          setStatus({ loading: false, message: "Trip updated and versioned", tone: "success" });
        } else {
          await api(
            "/api/trips/",
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            },
            true
          );
          setStatus({ loading: false, message: "Trip draft created", tone: "success" });
        }
        await loadTrips();
        if (selectedTripId) {
          await loadTripVersions(selectedTripId);
        }
      } catch (error) {
        setTripFormError(error.message);
        setStatus({ loading: false, message: error.message, tone: "danger" });
      }
    },
    [api, loadTripVersions, loadTrips, selectedTripId, setStatus, tripForm]
  );

  const startTripEdit = useCallback(
    (trip) => {
      setSelectedTripId(String(trip.id));
      setTripForm((prev) => ({
        ...prev,
        title: trip.title || "",
        origin: trip.origin || "",
        destination: trip.destination || "",
        service_date: trip.service_date || "",
        pickup_window_start: trip.pickup_window_start || "",
        pickup_window_end: trip.pickup_window_end || "",
        timezone_id: trip.timezone_id || "UTC",
        signup_deadline: trip.signup_deadline || "",
        capacity_limit: trip.capacity_limit || 4,
        pricing_model: trip.pricing_model || "flat",
        fare_cents: trip.fare_cents || 0,
        tax_bps: trip.tax_bps || 0,
        fee_cents: trip.fee_cents || 0,
        cancellation_cutoff_minutes: trip.cancellation_cutoff_minutes || 60,
        waypoints_text: (trip.waypoints || [])
          .map((waypoint) => `${waypoint.name || ""}|${waypoint.address || ""}`)
          .join("\n"),
      }));
      loadTripVersions(trip.id);
    },
    [loadTripVersions]
  );

  const handleFareEstimate = useCallback(
    async (event) => {
      event.preventDefault();
      try {
        const data = await api(`/api/trips/${fareForm.trip_id}/fare-estimate/?seats=${fareForm.seats}`);
        setFareForm((prev) => ({ ...prev, total_cents: data.total_cents }));
      } catch (error) {
        setStatus({ loading: false, message: error.message, tone: "danger" });
      }
    },
    [api, fareForm.seats, fareForm.trip_id, setStatus]
  );

  const handleBookingAction = useCallback(
    async (action, bookingId, payload = {}) => {
      try {
        const endpoints = bookingActionEndpoints(bookingId);
        const method = action === "timeline" ? "GET" : "POST";
        const data = await api(
          endpoints[action],
          method === "POST"
            ? {
                method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
              }
            : { method },
          method === "POST"
        );
        if (action === "timeline") {
          setBookingTimeline(data || []);
        }
        await Promise.all([loadMyBookings(), loadTripBookings(selectedTripId)]);
        setStatus({ loading: false, message: "Booking workflow updated", tone: "success" });
      } catch (error) {
        setStatus({ loading: false, message: error.message, tone: "danger" });
      }
    },
    [api, loadMyBookings, loadTripBookings, selectedTripId, setStatus]
  );

  const resetTrips = useCallback(() => {
    setTrips([]);
    setTripBookings([]);
    setMyBookings([]);
    setBookingTimeline([]);
    setSelectedTripId("");
    setFareForm(initialFareForm);
    setTripForm(initialTripForm);
    setTripFormError("");
    setTripVersions([]);
    setTripDiffLabels([]);
  }, []);

  return {
    trips,
    tripBookings,
    myBookings,
    bookingTimeline,
    selectedTripId,
    setSelectedTripId,
    fareForm,
    setFareForm,
    tripForm,
    setTripForm,
    tripFormError,
    tripVersions,
    tripDiffLabels,
    loadTrips,
    loadMyBookings,
    handlePublish,
    handleTripSubmit,
    startTripEdit,
    handleFareEstimate,
    handleBookingAction,
    loadTripVersions,
    resetTrips,
  };
}
