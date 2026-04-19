from django.contrib import admin

from trips.models import (
    Booking,
    BookingEvent,
    RefundRecord,
    Trip,
    TripVersion,
    TripWaypoint,
)

admin.site.register(Trip)
admin.site.register(TripWaypoint)
admin.site.register(TripVersion)
admin.site.register(Booking)
admin.site.register(BookingEvent)
admin.site.register(RefundRecord)
