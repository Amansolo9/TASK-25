import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("warehouse", "0001_initial"),
        ("inventory", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="inventorytask",
            name="location",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to="warehouse.location"
            ),
        ),
        migrations.AddField(
            model_name="inventorytask",
            name="plan",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tasks",
                to="inventory.inventoryplan",
            ),
        ),
        migrations.AddField(
            model_name="inventorycountline",
            name="task",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="count_lines",
                to="inventory.inventorytask",
            ),
        ),
        migrations.AddField(
            model_name="varianceclosure",
            name="line",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="variance_closure",
                to="inventory.inventorycountline",
            ),
        ),
        migrations.AddField(
            model_name="varianceclosure",
            name="reviewer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="variance_closures",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
