import csv
import hashlib
import os
from datetime import timedelta
from pathlib import Path

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from jobs.models import (
    IngestAttachmentFingerprint,
    IngestRowError,
    Job,
    JobCheckpoint,
    JobDependency,
    JobFailure,
    JobLease,
    JobStatus,
)


DEFAULT_ORG_CONCURRENCY_LIMIT = 3
MAX_ORG_CONCURRENCY_LIMIT = 20


def resolve_concurrency_limit(raw_value=None):
    candidate = (
        raw_value
        if raw_value is not None
        else os.getenv(
            "OFFLINE_INGEST_CONCURRENCY_LIMIT", str(DEFAULT_ORG_CONCURRENCY_LIMIT)
        )
    )
    try:
        parsed = int(str(candidate).strip())
    except (TypeError, ValueError):
        parsed = DEFAULT_ORG_CONCURRENCY_LIMIT

    if parsed < 1:
        return 1
    if parsed > MAX_ORG_CONCURRENCY_LIMIT:
        return MAX_ORG_CONCURRENCY_LIMIT
    return parsed


def validate_dependency_graph(job, dependency_ids):
    if job.id in dependency_ids:
        raise ValueError("Job cannot depend on itself")

    visited = set()

    def dfs(node_id):
        if node_id in visited:
            return False
        visited.add(node_id)
        parents = list(
            JobDependency.objects.filter(job_id=node_id).values_list(
                "depends_on_id", flat=True
            )
        )
        if job.id in parents:
            return True
        return any(dfs(parent_id) for parent_id in parents)

    for dep_id in dependency_ids:
        if dfs(dep_id):
            raise ValueError("Dependency cycle detected")


def has_unfinished_dependencies(job):
    return JobDependency.objects.filter(
        job=job,
        depends_on__status__in=[
            JobStatus.PENDING,
            JobStatus.RUNNING,
            JobStatus.BLOCKED,
        ],
    ).exists()


@transaction.atomic
def claim_next_job(worker_id, organization_id, concurrency_limit=3):
    concurrency_limit = resolve_concurrency_limit(concurrency_limit)
    active_count = JobLease.objects.filter(
        job__organization_id=organization_id,
        job__status=JobStatus.RUNNING,
        lease_until__gt=timezone.now(),
    ).count()
    if active_count >= concurrency_limit:
        return None

    stale_time = timezone.now()
    JobLease.objects.filter(lease_until__lte=stale_time).delete()

    candidate = (
        Job.objects.select_for_update()
        .filter(
            organization_id=organization_id,
            status=JobStatus.PENDING,
            next_run_at__lte=timezone.now(),
        )
        .filter(Q(lease__isnull=True) | Q(lease__lease_until__lte=timezone.now()))
        .order_by("priority", "created_at")
        .first()
    )
    if not candidate:
        return None

    if has_unfinished_dependencies(candidate):
        candidate.status = JobStatus.BLOCKED
        candidate.save(update_fields=["status"])
        return None

    candidate.status = JobStatus.RUNNING
    candidate.started_at = timezone.now()
    candidate.save(update_fields=["status", "started_at"])
    JobLease.objects.update_or_create(
        job=candidate,
        defaults={
            "worker_id": worker_id,
            "lease_until": timezone.now() + timedelta(minutes=2),
        },
    )
    return candidate


def heartbeat(job, worker_id):
    lease = require_lease_owner(job, worker_id)
    lease.lease_until = timezone.now() + timedelta(minutes=2)
    lease.save(update_fields=["lease_until", "heartbeat_at"])


def require_lease_owner(job, worker_id):
    lease = getattr(job, "lease", None)
    if not lease or lease.lease_until <= timezone.now():
        raise ValueError("Active lease required")
    if lease.worker_id != worker_id:
        raise ValueError("Lease is owned by another worker")
    return lease


def mark_job_success(job):
    job.status = JobStatus.SUCCESS
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "finished_at"])
    JobLease.objects.filter(job=job).delete()
    Job.objects.filter(status=JobStatus.BLOCKED).update(status=JobStatus.PENDING)


def mark_job_failure(job, exc):
    job.attempt_count += 1
    JobFailure.objects.create(
        job=job,
        attempt=job.attempt_count,
        error_type=exc.__class__.__name__,
        error_message=str(exc),
    )
    if job.attempt_count >= job.max_attempts:
        job.status = JobStatus.FAILED
        job.finished_at = timezone.now()
    else:
        job.status = JobStatus.PENDING
        job.schedule_next_retry()
    job.save(update_fields=["attempt_count", "status", "next_run_at", "finished_at"])
    JobLease.objects.filter(job=job).delete()


def _folder_attachments_checkpoint(job):
    checkpoint, _ = JobCheckpoint.objects.get_or_create(
        job=job,
        file_name="__attachments__",
        defaults={
            "row_offset": 0,
            "attachment_index": 0,
            "state_json": {},
        },
    )
    return checkpoint


def process_folder_ingest_job(job, fail_after_rows=None):
    source_path = Path(job.source_path or "")
    if not source_path.exists() or not source_path.is_dir():
        raise FileNotFoundError(f"Ingest source folder does not exist: {source_path}")

    csv_files = sorted(source_path.glob("*.csv"))
    image_files = sorted(
        [
            *source_path.glob("*.jpg"),
            *source_path.glob("*.jpeg"),
            *source_path.glob("*.png"),
        ]
    )

    processed_rows = 0
    row_errors = 0
    imported_rows = 0

    for csv_file in csv_files:
        checkpoint, _ = JobCheckpoint.objects.get_or_create(
            job=job,
            file_name=csv_file.name,
            defaults={
                "row_offset": 0,
                "attachment_index": 0,
                "state_json": {},
            },
        )

        with csv_file.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row_number, row in enumerate(reader, start=1):
                if row_number <= checkpoint.row_offset:
                    continue

                rider_id = (row.get("rider_id") or "").strip()
                trip_id = (row.get("trip_id") or "").strip()

                if not rider_id or not trip_id:
                    IngestRowError.objects.get_or_create(
                        job=job,
                        source_file=csv_file.name,
                        row_number=row_number,
                        defaults={
                            "error_message": "Missing required rider_id or trip_id",
                            "raw_row_json": row,
                        },
                    )
                    row_errors += 1
                else:
                    imported_rows += 1

                checkpoint.row_offset = row_number
                checkpoint.state_json = {
                    "last_rider_id": rider_id,
                    "last_trip_id": trip_id,
                }
                checkpoint.save(
                    update_fields=["row_offset", "state_json", "updated_at"]
                )
                processed_rows += 1

                if fail_after_rows and processed_rows >= fail_after_rows:
                    raise RuntimeError("Simulated ingest failure for checkpoint resume")

    attachment_checkpoint = _folder_attachments_checkpoint(job)
    start_index = attachment_checkpoint.attachment_index
    for attachment_index, image_file in enumerate(image_files, start=0):
        if attachment_index < start_index:
            continue
        payload = image_file.read_bytes()
        content_hash = hashlib.sha256(payload).hexdigest()
        IngestAttachmentFingerprint.objects.get_or_create(
            organization=job.organization,
            source_signature=str(image_file.relative_to(source_path)),
            content_hash=content_hash,
            defaults={"first_seen_job": job},
        )
        attachment_checkpoint.attachment_index = attachment_index + 1
        attachment_checkpoint.save(update_fields=["attachment_index", "updated_at"])

    return {
        "processed_rows": processed_rows,
        "imported_rows": imported_rows,
        "row_errors": row_errors,
        "csv_files": len(csv_files),
        "image_files": len(image_files),
    }


def run_folder_ingest_job(job, fail_after_rows=None):
    try:
        stats = process_folder_ingest_job(job, fail_after_rows=fail_after_rows)
    except Exception as exc:
        mark_job_failure(job, exc)
        raise
    mark_job_success(job)
    return stats
