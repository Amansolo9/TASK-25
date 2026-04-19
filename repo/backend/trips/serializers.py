from rest_framework import serializers

from trips.models import (
    Booking,
    BookingEvent,
    RefundRecord,
    Trip,
    TripVersion,
    TripWaypoint,
)


class TripWaypointSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripWaypoint
        fields = ["sequence", "name", "address"]


class TripSerializer(serializers.ModelSerializer):
    waypoints = TripWaypointSerializer(many=True, read_only=True)

    class Meta:
        model = Trip
        fields = [
            "id",
            "title",
            "origin",
            "destination",
            "service_date",
            "pickup_window_start",
            "pickup_window_end",
            "timezone_id",
            "signup_deadline",
            "status",
            "capacity_limit",
            "pricing_model",
            "fare_cents",
            "tax_bps",
            "fee_cents",
            "cancellation_cutoff_minutes",
            "current_version",
            "published_at",
            "waypoints",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "current_version",
            "published_at",
            "created_at",
            "updated_at",
        ]


class TripVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripVersion
        fields = [
            "id",
            "version_number",
            "change_summary",
            "material_change",
            "snapshot_json",
            "created_at",
        ]


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "id",
            "trip",
            "rider",
            "status",
            "care_priority",
            "acknowledged_version",
            "reack_required",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "trip",
            "rider",
            "acknowledged_version",
            "reack_required",
            "created_at",
            "updated_at",
        ]


class BookingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingEvent
        fields = [
            "id",
            "from_status",
            "to_status",
            "reason",
            "actor",
            "created_at",
        ]


class RefundRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundRecord
        fields = [
            "id",
            "booking",
            "amount_cents",
            "reason",
            "status",
            "requested_by",
            "approved_by",
            "created_at",
            "processed_at",
        ]
        read_only_fields = [
            "status",
            "requested_by",
            "approved_by",
            "created_at",
            "processed_at",
        ]
