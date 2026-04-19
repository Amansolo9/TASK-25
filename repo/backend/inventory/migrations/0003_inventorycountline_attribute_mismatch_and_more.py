from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventorycountline",
            name="attribute_mismatch",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="inventorycountline",
            name="observed_asset_code",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="inventorycountline",
            name="observed_location_code",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
