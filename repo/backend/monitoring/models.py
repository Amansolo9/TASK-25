from django.db import models

from organizations.models import Organization


class AlertSeverity(models.TextChoices):
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    CRITICAL = "critical", "Critical"


class AnomalyAlert(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="anomaly_alerts",
    )
    alert_type = models.CharField(max_length=120)
    severity = models.CharField(max_length=20, choices=AlertSeverity.choices)
    title = models.CharField(max_length=255)
    details = models.TextField()
    metadata_json = models.JSONField(default=dict)
    acknowledged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class AlertThreshold(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="alert_thresholds",
    )
    alert_type = models.CharField(max_length=120)
    numeric_threshold = models.PositiveIntegerField()
    window_minutes = models.PositiveIntegerField(default=60)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "alert_type"],
                name="uniq_org_alert_threshold",
            )
        ]
