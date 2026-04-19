import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Job",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("job_type", models.CharField(max_length=80)),
                ("source_path", models.CharField(blank=True, max_length=500)),
                ("payload_json", models.JSONField(default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                            ("blocked", "Blocked"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "trigger_type",
                    models.CharField(
                        choices=[("manual", "Manual"), ("scheduled", "Scheduled")],
                        max_length=20,
                    ),
                ),
                ("priority", models.PositiveSmallIntegerField(default=5)),
                ("dedupe_key", models.CharField(blank=True, max_length=120)),
                ("attempt_count", models.PositiveSmallIntegerField(default=0)),
                ("max_attempts", models.PositiveSmallIntegerField(default=4)),
                (
                    "next_run_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="jobs",
                        to="organizations.organization",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="IngestRowError",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("source_file", models.CharField(max_length=255)),
                ("row_number", models.PositiveIntegerField()),
                ("error_message", models.TextField()),
                ("raw_row_json", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="row_errors",
                        to="jobs.job",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="JobCheckpoint",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("file_name", models.CharField(max_length=255)),
                ("row_offset", models.PositiveIntegerField(default=0)),
                ("attachment_index", models.PositiveIntegerField(default=0)),
                ("state_json", models.JSONField(default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="checkpoints",
                        to="jobs.job",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="JobDependency",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "depends_on",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dependents",
                        to="jobs.job",
                    ),
                ),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dependencies",
                        to="jobs.job",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="JobFailure",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("attempt", models.PositiveSmallIntegerField()),
                ("error_type", models.CharField(max_length=120)),
                ("error_message", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="failures",
                        to="jobs.job",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="JobLease",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("worker_id", models.CharField(max_length=100)),
                ("lease_until", models.DateTimeField()),
                ("heartbeat_at", models.DateTimeField(auto_now=True)),
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lease",
                        to="jobs.job",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="job",
            index=models.Index(
                fields=["organization", "status", "priority", "next_run_at"],
                name="jobs_org_queue_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="jobdependency",
            constraint=models.UniqueConstraint(
                fields=("job", "depends_on"), name="uniq_job_dependency"
            ),
        ),
    ]
