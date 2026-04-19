from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from audit.models import AuditEvent
from jobs.models import JobFailure
from monitoring.models import AlertSeverity, AlertThreshold, AnomalyAlert
from organizations.models import Organization


DEFAULT_THRESHOLDS = {
    "failed_logins": 10,
    "job_failure_spike": 20,
    "bulk_exports": 5,
}


class Command(BaseCommand):
    help = "Detect local anomalies and create in-app alerts"

    def handle(self, *args, **options):
        now = timezone.now()
        window_start = now - timedelta(hours=1)

        for org in Organization.objects.filter(is_active=True):
            self._detect_failed_logins(org, window_start)
            self._detect_job_failure_spike(org, window_start)
            self._detect_bulk_exports(org, window_start)

        self.stdout.write(self.style.SUCCESS("Anomaly scan complete"))

    def _threshold(self, org, alert_type):
        custom = AlertThreshold.objects.filter(
            organization=org, alert_type=alert_type
        ).first()
        if custom:
            return custom.numeric_threshold
        return DEFAULT_THRESHOLDS[alert_type]

    def _detect_failed_logins(self, org, window_start):
        count = AuditEvent.objects.filter(
            organization=org,
            event_type="auth.login.failed",
            created_at__gte=window_start,
        ).count()
        if count >= self._threshold(org, "failed_logins"):
            AnomalyAlert.objects.create(
                organization=org,
                alert_type="failed_logins",
                severity=AlertSeverity.WARNING,
                title="Repeated failed logins",
                details=f"{count} failed logins in the last hour",
                metadata_json={"count": count},
            )

    def _detect_job_failure_spike(self, org, window_start):
        count = JobFailure.objects.filter(
            job__organization=org,
            created_at__gte=window_start,
        ).count()
        if count >= self._threshold(org, "job_failure_spike"):
            AnomalyAlert.objects.create(
                organization=org,
                alert_type="job_failure_spike",
                severity=AlertSeverity.CRITICAL,
                title="Job failure spike",
                details=f"{count} job failures in the last hour",
                metadata_json={"count": count},
            )

    def _detect_bulk_exports(self, org, window_start):
        count = AuditEvent.objects.filter(
            organization=org,
            event_type="export.unmasked.requested",
            created_at__gte=window_start,
        ).count()
        if count >= self._threshold(org, "bulk_exports"):
            AnomalyAlert.objects.create(
                organization=org,
                alert_type="bulk_exports",
                severity=AlertSeverity.WARNING,
                title="Bulk export requests",
                details=f"{count} unmasked exports requested in the last hour",
                metadata_json={"count": count},
            )
