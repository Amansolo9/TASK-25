from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from organizations.models import Organization


class JobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    BLOCKED = "blocked", "Blocked"


class JobTriggerType(models.TextChoices):
    MANUAL = "manual", "Manual"
    SCHEDULED = "scheduled", "Scheduled"


class Job(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="jobs",
    )
    job_type = models.CharField(max_length=80)
    source_path = models.CharField(max_length=500, blank=True)
    payload_json = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20, choices=JobStatus.choices, default=JobStatus.PENDING
    )
    trigger_type = models.CharField(max_length=20, choices=JobTriggerType.choices)
    priority = models.PositiveSmallIntegerField(default=5)
    dedupe_key = models.CharField(max_length=120, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=4)
    next_run_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["organization", "status", "priority", "next_run_at"],
                name="jobs_org_queue_idx",
            )
        ]

    def schedule_next_retry(self):
        backoff_minutes = [1, 5, 15]
        if self.attempt_count <= len(backoff_minutes):
            self.next_run_at = timezone.now() + timedelta(
                minutes=backoff_minutes[self.attempt_count - 1]
            )
        else:
            self.status = JobStatus.FAILED


class JobDependency(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="dependencies")
    depends_on = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="dependents"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["job", "depends_on"], name="uniq_job_dependency"
            )
        ]


class JobCheckpoint(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="checkpoints")
    file_name = models.CharField(max_length=255)
    row_offset = models.PositiveIntegerField(default=0)
    attachment_index = models.PositiveIntegerField(default=0)
    state_json = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)


class JobLease(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="lease")
    worker_id = models.CharField(max_length=100)
    lease_until = models.DateTimeField()
    heartbeat_at = models.DateTimeField(auto_now=True)


class JobFailure(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="failures")
    attempt = models.PositiveSmallIntegerField()
    error_type = models.CharField(max_length=120)
    error_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class IngestRowError(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="row_errors")
    source_file = models.CharField(max_length=255)
    row_number = models.PositiveIntegerField()
    error_message = models.TextField()
    raw_row_json = models.JSONField(default=dict)
    resolved = models.BooleanField(default=False)
    resolution_note = models.CharField(max_length=255, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_ingest_row_errors",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class IngestAttachmentFingerprint(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="attachment_fingerprints",
    )
    source_signature = models.CharField(max_length=255)
    content_hash = models.CharField(max_length=128)
    first_seen_job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attachment_fingerprints",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "source_signature", "content_hash"],
                name="uniq_attachment_fingerprint",
            )
        ]
