import os
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from jobs.models import Job, JobStatus, JobTriggerType
from jobs.services import (
    claim_next_job,
    resolve_concurrency_limit,
    run_folder_ingest_job,
)
from organizations.models import Organization


class Command(BaseCommand):
    help = "Run offline folder ingest worker with checkpoint resume"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--interval-seconds", type=int, default=30)
        parser.add_argument("--schedule", action="store_true")
        parser.add_argument("--scan-folder", action="append", dest="scan_folders")
        parser.add_argument("--simulate-failure-after-rows", type=int)

    def _configured_scan_folders(self, options):
        folders = list(options.get("scan_folders") or [])
        env_folders = [
            item.strip()
            for item in os.getenv("OFFLINE_INGEST_FOLDERS", "").split(",")
            if item.strip()
        ]
        folders.extend(env_folders)
        deduped = []
        seen = set()
        for folder in folders:
            normalized = str(Path(folder).expanduser())
            if normalized not in seen:
                deduped.append(normalized)
                seen.add(normalized)
        return deduped

    def _enqueue_scheduled_jobs(self, folders):
        created = 0
        if not folders:
            return created

        now_bucket = timezone.now().strftime("%Y%m%d%H%M")
        org_ids = list(
            Organization.objects.filter(is_active=True).values_list("id", flat=True)
        )
        for org_id in org_ids:
            for folder in folders:
                dedupe_key = f"scheduled-folder-scan:{folder}:{now_bucket}"
                _, was_created = Job.objects.get_or_create(
                    organization_id=org_id,
                    job_type="ingest.folder_scan",
                    dedupe_key=dedupe_key,
                    defaults={
                        "source_path": folder,
                        "payload_json": {"scan_mode": "scheduled"},
                        "status": JobStatus.PENDING,
                        "trigger_type": JobTriggerType.SCHEDULED,
                        "priority": 4,
                        "next_run_at": timezone.now(),
                    },
                )
                if was_created:
                    created += 1
        return created

    def _next_pending_jobs(self):
        worker_id = os.getenv("OFFLINE_INGEST_WORKER_ID", "offline-ingest-worker")
        concurrency_limit = resolve_concurrency_limit()
        jobs = []
        org_ids = list(
            Organization.objects.filter(is_active=True).values_list("id", flat=True)
        )
        for org_id in org_ids:
            claimed = claim_next_job(
                worker_id=worker_id,
                organization_id=org_id,
                concurrency_limit=concurrency_limit,
            )
            if claimed and claimed.job_type in [
                "ingest.folder_scan",
                "ingest.manifest",
            ]:
                jobs.append(claimed)
        return jobs

    def _run_once(self, options):
        folders = self._configured_scan_folders(options)
        if options["schedule"]:
            created = self._enqueue_scheduled_jobs(folders)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Enqueued {created} scheduled ingest jobs")
                )

        jobs = self._next_pending_jobs()
        if not jobs:
            self.stdout.write("No pending ingest jobs")
            return

        for job in jobs:
            self.stdout.write(
                f"Processing job #{job.id} ({job.job_type}) from {job.source_path}"
            )
            try:
                stats = run_folder_ingest_job(
                    job,
                    fail_after_rows=options.get("simulate_failure_after_rows"),
                )
            except Exception as exc:
                self.stderr.write(
                    self.style.WARNING(
                        f"Job #{job.id} failed attempt {job.attempt_count}: {exc}"
                    )
                )
                continue
            self.stdout.write(
                self.style.SUCCESS(
                    f"Job #{job.id} success imported_rows={stats['imported_rows']} row_errors={stats['row_errors']}"
                )
            )

    def handle(self, *args, **options):
        interval = max(5, int(options["interval_seconds"]))
        if options["once"]:
            self._run_once(options)
            return

        self.stdout.write("Starting offline ingest worker loop")
        while True:
            self._run_once(options)
            time.sleep(interval)
