from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("security", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="apiclientkey",
            name="secret_encrypted",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="apiclientkey",
            name="secret_fingerprint",
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
