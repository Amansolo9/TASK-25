from django.urls import path

from monitoring.views import (
    AlertThresholdListCreateView,
    AnomalyAlertAcknowledgeView,
    AnomalyAlertListView,
)

urlpatterns = [
    path("alerts/", AnomalyAlertListView.as_view(), name="anomaly-alerts"),
    path(
        "alerts/<int:alert_id>/ack/",
        AnomalyAlertAcknowledgeView.as_view(),
        name="anomaly-alert-ack",
    ),
    path(
        "thresholds/", AlertThresholdListCreateView.as_view(), name="alert-thresholds"
    ),
]
