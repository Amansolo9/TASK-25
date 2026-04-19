from django.urls import path

from trips.views import (
    BookingAcknowledgeView,
    BookingCancelView,
    BookingCreateView,
    BookingNoShowView,
    BookingRefundDecisionView,
    BookingRefundRequestView,
    BookingTimelineView,
    MyBookingListView,
    TripDetailView,
    TripFareEstimateView,
    TripListCreateView,
    TripPublishView,
    TripUnpublishView,
    TripVersionListView,
)

urlpatterns = [
    path("", TripListCreateView.as_view(), name="trip-list-create"),
    path("<int:trip_id>/", TripDetailView.as_view(), name="trip-detail"),
    path("<int:trip_id>/publish/", TripPublishView.as_view(), name="trip-publish"),
    path(
        "<int:trip_id>/unpublish/", TripUnpublishView.as_view(), name="trip-unpublish"
    ),
    path(
        "<int:trip_id>/versions/",
        TripVersionListView.as_view(),
        name="trip-version-list",
    ),
    path("<int:trip_id>/bookings/", BookingCreateView.as_view(), name="booking-create"),
    path(
        "<int:trip_id>/fare-estimate/",
        TripFareEstimateView.as_view(),
        name="trip-fare-estimate",
    ),
    path("bookings/mine/", MyBookingListView.as_view(), name="my-bookings"),
    path(
        "bookings/<int:booking_id>/ack/",
        BookingAcknowledgeView.as_view(),
        name="booking-ack",
    ),
    path(
        "bookings/<int:booking_id>/cancel/",
        BookingCancelView.as_view(),
        name="booking-cancel",
    ),
    path(
        "bookings/<int:booking_id>/no-show/",
        BookingNoShowView.as_view(),
        name="booking-no-show",
    ),
    path(
        "bookings/<int:booking_id>/refund-request/",
        BookingRefundRequestView.as_view(),
        name="booking-refund-request",
    ),
    path(
        "bookings/<int:booking_id>/refund-decision/",
        BookingRefundDecisionView.as_view(),
        name="booking-refund-decision",
    ),
    path(
        "bookings/<int:booking_id>/timeline/",
        BookingTimelineView.as_view(),
        name="booking-timeline",
    ),
]
