from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_comparisonitem_uniq_user_comparison_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="travelerprofile",
            name="encrypted_credential_number",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="travelerprofile",
            name="encrypted_government_id",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="verificationdocument",
            name="secure_storage_ref",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="verificationdocument",
            name="uploaded_file",
            field=models.FileField(blank=True, upload_to="verification_docs/%Y/%m/%d"),
        ),
    ]
