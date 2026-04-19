from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_traveler_sensitive_fields_and_verification_upload"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="verificationreview",
            constraint=models.UniqueConstraint(
                fields=("verification_request", "reviewer"),
                name="uniq_verification_review_per_reviewer",
            ),
        ),
    ]
