from django.db import transaction
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from access.services import is_platform_admin, user_has_permission
from audit.services import record_audit_event
from core.authz import require_permission
from core.structured_logging import log_app_event
from organizations.models import Organization
from trips.models import (
    Booking,
    BookingEvent,
    BookingStatus,
    RefundStatus,
    Trip,
    TripStatus,
    TripVersion,
    TripWaypoint,
)
from trips.serializers import (
    BookingEventSerializer,
    BookingSerializer,
    RefundRecordSerializer,
    TripSerializer,
    TripWaypointSerializer,
    TripVersionSerializer,
)
from trips.services import (
    apply_capacity_policy,
    calculate_total_fare_cents,
    can_cancel_booking,
    create_refund_request,
    has_material_change,
    make_trip_snapshot,
    transition_booking_status,
)


def _booking_reack_conflict_response(booking_id):
    log_app_event("trips", "booking.reack_required.blocked", booking_id=booking_id)
    return Response(
        {
            "detail": "Trip update acknowledgment is required before this action.",
            "code": "reack_required",
            "booking_id": booking_id,
        },
        status=409,
    )


def _validation_error_response(exc):
    if hasattr(exc, "message_dict"):
        return Response({"detail": exc.message_dict}, status=400)
    return Response(
        {"detail": exc.messages if hasattr(exc, "messages") else str(exc)}, status=400
    )


def _target_organization(request):
    org_id = request.data.get("organization_id") or request.GET.get("organization_id")
    if is_platform_admin(request.user) and org_id:
        return Organization.objects.filter(id=org_id, is_active=True).first()
    return request.user.organization


def _org_scope_kwargs(request, field_name):
    if is_platform_admin(request.user):
        org_id = request.GET.get("organization_id") or request.data.get(
            "organization_id"
        )
        if org_id:
            return {field_name: org_id}
        return {}
    return {field_name: request.user.organization_id}


def _normalized_waypoints(waypoints):
    def _sequence(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    return [
        {
            "sequence": _sequence(item.get("sequence")),
            "name": item.get("name"),
            "address": item.get("address"),
        }
        for item in sorted(waypoints, key=lambda item: _sequence(item.get("sequence")))
    ]


def _replace_trip_waypoints(trip, raw_waypoints):
    serializer = TripWaypointSerializer(data=raw_waypoints, many=True)
    serializer.is_valid(raise_exception=True)
    sequences = sorted(item["sequence"] for item in serializer.validated_data)
    expected = list(range(1, len(sequences) + 1))
    if sequences != expected:
        raise serializers.ValidationError(
            {
                "waypoints": [
                    "sequence values must be unique contiguous integers starting at 1."
                ]
            }
        )
    TripWaypoint.objects.filter(trip=trip).delete()
    TripWaypoint.objects.bulk_create(
        [TripWaypoint(trip=trip, **item) for item in serializer.validated_data]
    )
    return serializer.validated_data


class TripListCreateView(APIView):
    def get(self, request):
        if not user_has_permission(request.user, "trip.read"):
            return Response({"detail": "Missing permission: trip.read"}, status=403)
        queryset = Trip.objects.filter(
            **_org_scope_kwargs(request, "organization_id")
        ).order_by("pickup_window_start")
        return Response(TripSerializer(queryset, many=True).data)

    @transaction.atomic
    def post(self, request):
        if not user_has_permission(request.user, "trip.write"):
            return Response({"detail": "Missing permission: trip.write"}, status=403)

        serializer = TripSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = _target_organization(request)
        if organization is None:
            return Response(
                {"detail": "Valid organization_id is required."}, status=400
            )
        trip = Trip(
            organization=organization,
            created_by=request.user,
            updated_by=request.user,
            **serializer.validated_data,
        )
        try:
            trip.full_clean()
        except ValidationError as exc:
            return _validation_error_response(exc)
        trip.save()

        waypoints = request.data.get("waypoints", None)
        if waypoints is not None:
            if not isinstance(waypoints, list):
                return Response(
                    {"detail": {"waypoints": ["Must be a list."]}}, status=400
                )
            _replace_trip_waypoints(trip, waypoints)

        TripVersion.objects.create(
            trip=trip,
            version_number=trip.current_version,
            changed_by=request.user,
            change_summary="Initial draft",
            material_change=False,
            snapshot_json=make_trip_snapshot(trip),
        )

        record_audit_event(
            event_type="trip.created",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="trip",
            resource_id=str(trip.id),
        )
        return Response(TripSerializer(trip).data, status=status.HTTP_201_CREATED)


class TripDetailView(APIView):
    @transaction.atomic
    def patch(self, request, trip_id):
        if not user_has_permission(request.user, "trip.write"):
            return Response({"detail": "Missing permission: trip.write"}, status=403)

        trip = get_object_or_404(
            Trip.objects.select_for_update(),
            id=trip_id,
            **_org_scope_kwargs(request, "organization_id"),
        )
        serializer = TripSerializer(trip, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        existing_waypoints = _normalized_waypoints(
            list(trip.waypoints.values("sequence", "name", "address"))
        )

        material_change = has_material_change(trip, serializer.validated_data)
        waypoint_payload = request.data.get("waypoints", None)
        waypoint_changed = False
        if waypoint_payload is not None:
            if not isinstance(waypoint_payload, list):
                return Response(
                    {"detail": {"waypoints": ["Must be a list."]}}, status=400
                )
            normalized_new = _normalized_waypoints(waypoint_payload)
            waypoint_changed = normalized_new != existing_waypoints
            if waypoint_changed:
                material_change = True
        trip = serializer.save(updated_by=request.user)
        try:
            trip.full_clean()
        except ValidationError as exc:
            return _validation_error_response(exc)
        trip.save()

        if waypoint_payload is not None:
            _replace_trip_waypoints(trip, waypoint_payload)

        trip.current_version += 1
        trip.save(update_fields=["current_version", "updated_at"])

        if material_change and trip.bookings.exists():
            Booking.objects.filter(
                trip=trip,
                status__in=[BookingStatus.CONFIRMED, BookingStatus.WAITLISTED],
            ).update(reack_required=True)

        apply_capacity_policy(trip)

        TripVersion.objects.create(
            trip=trip,
            version_number=trip.current_version,
            changed_by=request.user,
            change_summary=request.data.get("change_summary", "Trip updated"),
            material_change=material_change,
            snapshot_json=make_trip_snapshot(trip),
        )

        record_audit_event(
            event_type="trip.updated",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="trip",
            resource_id=str(trip.id),
            metadata={
                "material_change": material_change,
                "version": trip.current_version,
            },
        )
        return Response(TripSerializer(trip).data)


class TripPublishView(APIView):
    def post(self, request, trip_id):
        if not user_has_permission(request.user, "trip.write"):
            return Response({"detail": "Missing permission: trip.write"}, status=403)

        trip = get_object_or_404(
            Trip, id=trip_id, **_org_scope_kwargs(request, "organization_id")
        )
        trip.status = TripStatus.LIVE
        trip.published_at = timezone.now()
        trip.updated_by = request.user
        trip.save(update_fields=["status", "published_at", "updated_by", "updated_at"])

        record_audit_event(
            event_type="trip.published",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="trip",
            resource_id=str(trip.id),
        )
        return Response(TripSerializer(trip).data)


class TripUnpublishView(APIView):
    def post(self, request, trip_id):
        if not user_has_permission(request.user, "trip.write"):
            return Response({"detail": "Missing permission: trip.write"}, status=403)

        trip = get_object_or_404(
            Trip, id=trip_id, **_org_scope_kwargs(request, "organization_id")
        )
        trip.status = TripStatus.UNPUBLISHED
        trip.updated_by = request.user
        trip.save(update_fields=["status", "updated_by", "updated_at"])

        record_audit_event(
            event_type="trip.unpublished",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="trip",
            resource_id=str(trip.id),
        )
        return Response(TripSerializer(trip).data)


class TripVersionListView(APIView):
    def get(self, request, trip_id):
        if not user_has_permission(request.user, "trip.read"):
            return Response({"detail": "Missing permission: trip.read"}, status=403)
        trip = get_object_or_404(
            Trip, id=trip_id, **_org_scope_kwargs(request, "organization_id")
        )
        versions = trip.versions.order_by("-version_number")
        return Response(TripVersionSerializer(versions, many=True).data)


class BookingCreateView(APIView):
    def get(self, request, trip_id):
        if not user_has_permission(request.user, "trip.read"):
            return Response({"detail": "Missing permission: trip.read"}, status=403)

        trip = get_object_or_404(
            Trip, id=trip_id, **_org_scope_kwargs(request, "organization_id")
        )

        can_view_all = user_has_permission(request.user, "trip.write")
        queryset = trip.bookings.select_related("rider").order_by("-created_at")
        if not can_view_all:
            queryset = queryset.filter(rider=request.user)

        return Response(BookingSerializer(queryset, many=True).data)

    def post(self, request, trip_id):
        if not user_has_permission(request.user, "booking.write"):
            return Response({"detail": "Missing permission: booking.write"}, status=403)

        trip = get_object_or_404(
            Trip, id=trip_id, organization=request.user.organization
        )
        serializer = BookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        confirmed_count = Booking.objects.filter(
            trip=trip,
            status=BookingStatus.CONFIRMED,
        ).count()
        status_value = (
            BookingStatus.CONFIRMED
            if confirmed_count < trip.capacity_limit
            else BookingStatus.WAITLISTED
        )

        booking = serializer.save(
            trip=trip,
            rider=request.user,
            status=status_value,
            acknowledged_version=trip.current_version,
        )

        BookingEvent.objects.create(
            booking=booking,
            from_status="",
            to_status=booking.status,
            actor=request.user,
            reason="Booking created",
        )

        record_audit_event(
            event_type="booking.created",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="booking",
            resource_id=str(booking.id),
            metadata={"trip_id": trip.id, "status": booking.status},
        )
        return Response(BookingSerializer(booking).data, status=201)


class BookingAcknowledgeView(APIView):
    def post(self, request, booking_id):
        denied = require_permission(request.user, "booking.write")
        if denied:
            return denied
        booking = get_object_or_404(
            Booking.objects.select_related("trip"),
            id=booking_id,
            rider=request.user,
            trip__organization=request.user.organization,
        )
        booking.acknowledged_version = booking.trip.current_version
        booking.reack_required = False
        booking.save(
            update_fields=["acknowledged_version", "reack_required", "updated_at"]
        )
        return Response(BookingSerializer(booking).data)


class MyBookingListView(APIView):
    def get(self, request):
        denied = require_permission(request.user, "booking.write")
        if denied:
            return denied
        queryset = Booking.objects.filter(
            rider=request.user,
            trip__organization=request.user.organization,
        ).order_by("-created_at")
        return Response(BookingSerializer(queryset, many=True).data)


class BookingCancelView(APIView):
    def post(self, request, booking_id):
        denied = require_permission(request.user, "booking.write")
        if denied:
            return denied
        booking = get_object_or_404(
            Booking.objects.select_related("trip"),
            id=booking_id,
            rider=request.user,
            trip__organization=request.user.organization,
        )
        if not can_cancel_booking(booking):
            return Response(
                {
                    "detail": "Cancellation cutoff has passed for this booking.",
                    "cutoff_minutes": booking.trip.cancellation_cutoff_minutes,
                },
                status=400,
            )
        if booking.reack_required:
            return _booking_reack_conflict_response(booking.id)
        try:
            transition_booking_status(
                booking=booking,
                target_status=BookingStatus.CANCELLED,
                actor=request.user,
                reason=request.data.get("reason", "Cancelled by rider"),
            )
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(BookingSerializer(booking).data)


class BookingNoShowView(APIView):
    def post(self, request, booking_id):
        if not user_has_permission(request.user, "trip.write"):
            return Response({"detail": "Missing permission: trip.write"}, status=403)
        booking = get_object_or_404(
            Booking.objects.select_related("trip"),
            id=booking_id,
            trip__organization=request.user.organization,
        )
        if timezone.now() < booking.trip.pickup_window_end:
            return Response(
                {"detail": "Cannot mark no-show before the trip pickup window ends."},
                status=400,
            )
        try:
            transition_booking_status(
                booking=booking,
                target_status=BookingStatus.NO_SHOW,
                actor=request.user,
                reason=request.data.get("reason", "Marked no-show"),
            )
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(BookingSerializer(booking).data)


class BookingRefundRequestView(APIView):
    def post(self, request, booking_id):
        denied = require_permission(request.user, "booking.write")
        if denied:
            return denied
        booking = get_object_or_404(
            Booking.objects.select_related("trip"),
            id=booking_id,
            rider=request.user,
            trip__organization=request.user.organization,
        )
        if booking.reack_required:
            return _booking_reack_conflict_response(booking.id)
        try:
            refund = create_refund_request(
                booking=booking,
                actor=request.user,
                reason=request.data.get("reason", "Refund requested by rider"),
            )
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(RefundRecordSerializer(refund).data, status=201)


class BookingRefundDecisionView(APIView):
    def post(self, request, booking_id):
        if not user_has_permission(request.user, "trip.write"):
            return Response({"detail": "Missing permission: trip.write"}, status=403)
        booking = get_object_or_404(
            Booking.objects.select_related("refund", "trip"),
            id=booking_id,
            trip__organization=request.user.organization,
        )
        if not hasattr(booking, "refund"):
            return Response(
                {"detail": "No refund request exists for this booking."}, status=404
            )
        decision = (request.data.get("decision") or "").strip().lower()
        if decision not in {RefundStatus.APPROVED, RefundStatus.REJECTED}:
            return Response(
                {"detail": "decision must be 'approved' or 'rejected'"}, status=400
            )

        if decision == RefundStatus.APPROVED:
            booking.refund.approve(request.user)
        else:
            booking.refund.reject(request.user)
        booking.refund.save(update_fields=["status", "approved_by", "processed_at"])
        return Response(RefundRecordSerializer(booking.refund).data)


class BookingTimelineView(APIView):
    def get(self, request, booking_id):
        booking = get_object_or_404(
            Booking,
            id=booking_id,
            trip__organization=request.user.organization,
        )
        is_owner = booking.rider_id == request.user.id
        is_ops_viewer = user_has_permission(request.user, "trip.write")
        if not is_owner and not is_ops_viewer:
            log_app_event(
                "trips",
                "booking.timeline.denied",
                booking_id=booking.id,
                actor_id=request.user.id,
                owner_id=booking.rider_id,
            )
            return Response(
                {"detail": "Not authorized to view this booking timeline."}, status=403
            )

        events = booking.events.order_by("created_at")
        return Response(BookingEventSerializer(events, many=True).data)


class TripFareEstimateView(APIView):
    def get(self, request, trip_id):
        if not user_has_permission(request.user, "trip.read"):
            return Response({"detail": "Missing permission: trip.read"}, status=403)
        trip = get_object_or_404(
            Trip, id=trip_id, organization=request.user.organization
        )
        seats = int(request.GET.get("seats", 1))
        if seats < 1:
            return Response({"detail": "seats must be >= 1"}, status=400)
        total = calculate_total_fare_cents(trip, seats=seats)
        return Response(
            {
                "trip_id": trip.id,
                "pricing_model": trip.pricing_model,
                "seats": seats,
                "fare_cents": trip.fare_cents,
                "fee_cents": trip.fee_cents,
                "tax_bps": trip.tax_bps,
                "total_cents": total,
            }
        )
