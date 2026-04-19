from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from trips.models import (
    Booking,
    BookingEvent,
    BookingStatus,
    PricingModel,
    RefundRecord,
)

MATERIAL_CHANGE_FIELDS = {
    "origin",
    "destination",
    "pickup_window_start",
    "pickup_window_end",
    "fare_cents",
    "capacity_limit",
    "signup_deadline",
}


def has_material_change(instance, validated_data):
    for field in MATERIAL_CHANGE_FIELDS:
        if field in validated_data and validated_data[field] != getattr(
            instance, field
        ):
            return True
    return False


@transaction.atomic
def apply_capacity_policy(trip):
    confirmed = list(
        Booking.objects.select_for_update()
        .filter(trip=trip, status=BookingStatus.CONFIRMED)
        .order_by("-care_priority", "created_at")
    )

    if len(confirmed) <= trip.capacity_limit:
        return

    keep = confirmed[: trip.capacity_limit]
    move = confirmed[trip.capacity_limit :]

    keep_ids = [booking.id for booking in keep]
    Booking.objects.filter(id__in=keep_ids).update(status=BookingStatus.CONFIRMED)

    move_ids = [booking.id for booking in move]
    Booking.objects.filter(id__in=move_ids).update(status=BookingStatus.WAITLISTED)


def make_trip_snapshot(trip):
    return {
        "trip_id": trip.id,
        "title": trip.title,
        "origin": trip.origin,
        "destination": trip.destination,
        "service_date": str(trip.service_date),
        "pickup_window_start": trip.pickup_window_start.isoformat(),
        "pickup_window_end": trip.pickup_window_end.isoformat(),
        "timezone_id": trip.timezone_id,
        "signup_deadline": trip.signup_deadline.isoformat(),
        "capacity_limit": trip.capacity_limit,
        "pricing_model": trip.pricing_model,
        "fare_cents": trip.fare_cents,
        "tax_bps": trip.tax_bps,
        "fee_cents": trip.fee_cents,
        "status": trip.status,
        "current_version": trip.current_version,
        "waypoints": [
            {
                "sequence": waypoint.sequence,
                "name": waypoint.name,
                "address": waypoint.address,
            }
            for waypoint in trip.waypoints.all()
        ],
    }


def calculate_total_fare_cents(trip, seats=1):
    base = (
        trip.fare_cents
        if trip.pricing_model == PricingModel.FLAT
        else trip.fare_cents * seats
    )
    subtotal = base + trip.fee_cents
    tax = int(round(subtotal * (trip.tax_bps / 10000)))
    return subtotal + tax


def ensure_transition_allowed(booking, target_status):
    allowed = {
        BookingStatus.CONFIRMED: {BookingStatus.CANCELLED, BookingStatus.NO_SHOW},
        BookingStatus.WAITLISTED: {BookingStatus.CANCELLED, BookingStatus.CONFIRMED},
        BookingStatus.CANCELLED: set(),
        BookingStatus.NO_SHOW: set(),
    }
    if target_status not in allowed.get(booking.status, set()):
        raise ValidationError(
            f"Invalid transition from {booking.status} to {target_status}."
        )


def can_cancel_booking(booking):
    trip = booking.trip
    cutoff = trip.pickup_window_start - timedelta(
        minutes=trip.cancellation_cutoff_minutes
    )
    return timezone.now() <= cutoff


@transaction.atomic
def transition_booking_status(*, booking, target_status, actor, reason=""):
    ensure_transition_allowed(booking, target_status)
    from_status = booking.status
    booking.status = target_status
    booking.save(update_fields=["status", "updated_at"])

    BookingEvent.objects.create(
        booking=booking,
        from_status=from_status,
        to_status=target_status,
        reason=reason,
        actor=actor,
    )
    return booking


@transaction.atomic
def create_refund_request(*, booking, actor, reason):
    if booking.status != BookingStatus.CANCELLED:
        raise ValidationError("Refund can only be requested for cancelled bookings.")
    amount = calculate_total_fare_cents(booking.trip, seats=1)
    refund, created = RefundRecord.objects.get_or_create(
        booking=booking,
        defaults={
            "amount_cents": amount,
            "reason": reason,
            "requested_by": actor,
        },
    )
    if not created and refund.status == "rejected":
        refund.status = "pending"
        refund.reason = reason
        refund.requested_by = actor
        refund.save(update_fields=["status", "reason", "requested_by"])
    return refund
