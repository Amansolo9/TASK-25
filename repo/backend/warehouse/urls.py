from django.urls import path

from warehouse.views import (
    LocationDetailView,
    LocationListCreateView,
    PartnerRecordDetailView,
    PartnerRecordListCreateView,
    WarehouseDetailView,
    WarehouseListCreateView,
    ZoneDetailView,
    ZoneListCreateView,
)

urlpatterns = [
    path("", WarehouseListCreateView.as_view(), name="warehouse-list-create"),
    path("<int:warehouse_id>/", WarehouseDetailView.as_view(), name="warehouse-detail"),
    path("zones/", ZoneListCreateView.as_view(), name="zone-list-create"),
    path("zones/<int:zone_id>/", ZoneDetailView.as_view(), name="zone-detail"),
    path("locations/", LocationListCreateView.as_view(), name="location-list-create"),
    path(
        "locations/<int:location_id>/",
        LocationDetailView.as_view(),
        name="location-detail",
    ),
    path(
        "partners/",
        PartnerRecordListCreateView.as_view(),
        name="partner-record-list-create",
    ),
    path(
        "partners/<int:partner_id>/",
        PartnerRecordDetailView.as_view(),
        name="partner-record-detail",
    ),
]
