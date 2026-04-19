from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_verification_review_unique_reviewer"),
    ]

    operations = [
        migrations.AddField(
            model_name="dataexportrequest",
            name="checksum_sha256",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="dataexportrequest",
            name="failure_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="dataexportrequest",
            name="file_size_bytes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="dataexportrequest",
            name="processed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
