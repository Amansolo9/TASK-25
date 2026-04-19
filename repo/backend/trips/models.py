from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from organizations.models import Organization


class TripStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    LIVE = "live", "Live"
    UNPUBLISHED = "unpublished", "Unpublished"


class PricingModel(models.TextChoices):
    FLAT = "flat", "Flat Fare"
    PER_SEAT = "per_seat", "Per Seat"


class BookingStatus(models.TextChoices):
    CONFIRMED = "confirmed", "Confirmed"
    WAITLISTED = "waitlisted", "Waitlisted"
    CANCELLED = "cancelled", "Cancelled"
    NO_SHOW = "no_show", "No Show"


class RefundStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Trip(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="trips",
    )
    title = models.CharField(max_length=255)
    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    service_date = models.DateField()
    pickup_window_start = models.DateTimeField()
    pickup_window_end = models.DateTimeField()
    timezone_id = models.CharField(max_length=64, default="UTC")
    signup_deadline = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=TripStatus.choices, default=TripStatus.DRAFT
    )
    capacity_limit = models.PositiveIntegerField()
    pricing_model = models.CharField(max_length=20, choices=PricingModel.choices)
    fare_cents = models.PositiveIntegerField(default=0)
    tax_bps = models.PositiveIntegerField(default=0)
    fee_cents = models.PositiveIntegerField(default=0)
    cancellation_cutoff_minutes = models.PositiveIntegerField(default=120)
    current_version = models.PositiveIntegerField(default=1)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_trips",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_trips",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.pickup_window_end <= self.pickup_window_start:
            raise ValidationError("Pickup window end must be after start.")

        minimum_deadline = self.pickup_window_start - timedelta(hours=2)
        if self.signup_deadline > minimum_deadline:
            raise ValidationError(
                "Signup deadline must be at least 2 hours before departure."
            )


class TripWaypoint(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="waypoints")
    sequence = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "sequence"],
                name="uniq_trip_waypoint_sequence",
            )
        ]


class TripVersion(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    change_summary = models.CharField(max_length=255, blank=True)
    material_change = models.BooleanField(default=False)
    snapshot_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "version_number"],
                name="uniq_trip_version_number",
            )
        ]


class Booking(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="bookings")
    rider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=BookingStatus.choices, default=BookingStatus.CONFIRMED
    )
    care_priority = models.PositiveIntegerField(default=0)
    acknowledged_version = models.PositiveIntegerField(default=1)
    reack_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "rider"],
                name="uniq_trip_rider_booking",
            )
        ]


class BookingEvent(models.Model):
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="events"
    )
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    reason = models.CharField(max_length=255, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)


class RefundRecord(models.Model):
    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="refund"
    )
    amount_cents = models.PositiveIntegerField()
    reason = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="requested_refunds",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_refunds",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def approve(self, approver):
        self.status = RefundStatus.APPROVED
        self.approved_by = approver
        self.processed_at = timezone.now()

    def reject(self, approver):
        self.status = RefundStatus.REJECTED
        self.approved_by = approver
        self.processed_at = timezone.now()
