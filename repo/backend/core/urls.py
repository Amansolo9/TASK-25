from django.urls import include, path

from core.views import HealthCheckView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("auth/", include("accounts.urls")),
    path("access/", include("access.urls")),
    path("trips/", include("trips.urls")),
    path("warehouses/", include("warehouse.urls")),
    path("inventory/", include("inventory.urls")),
    path("jobs/", include("jobs.urls")),
    path("monitoring/", include("monitoring.urls")),
    path("security/", include("security.urls")),
]
