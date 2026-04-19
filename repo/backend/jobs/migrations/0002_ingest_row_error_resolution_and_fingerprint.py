import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="ingestrowerror",
            name="resolution_note",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="ingestrowerror",
            name="resolved",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="ingestrowerror",
            name="resolved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ingestrowerror",
            name="resolved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="resolved_ingest_row_errors",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="IngestAttachmentFingerprint",
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
                ("source_signature", models.CharField(max_length=255)),
                ("content_hash", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "first_seen_job",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="attachment_fingerprints",
                        to="jobs.job",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachment_fingerprints",
                        to="organizations.organization",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="ingestattachmentfingerprint",
            constraint=models.UniqueConstraint(
                fields=("organization", "source_signature", "content_hash"),
                name="uniq_attachment_fingerprint",
            ),
        ),
    ]
