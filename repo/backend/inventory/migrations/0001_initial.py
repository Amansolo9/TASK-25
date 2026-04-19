import django.db.models.deletion
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
            name="InventoryCountLine",
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
                ("asset_code", models.CharField(max_length=120)),
                ("book_quantity", models.DecimalField(decimal_places=2, max_digits=14)),
                (
                    "physical_quantity",
                    models.DecimalField(decimal_places=2, max_digits=14),
                ),
                (
                    "variance_quantity",
                    models.DecimalField(decimal_places=2, default=0, max_digits=14),
                ),
                (
                    "variance_percent",
                    models.DecimalField(decimal_places=4, default=0, max_digits=9),
                ),
                (
                    "variance_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("missing", "Missing"),
                            ("extra", "Extra"),
                            ("data_mismatch", "Data Mismatch"),
                        ],
                        max_length=20,
                    ),
                ),
                ("requires_review", models.BooleanField(default=False)),
                ("closed", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="VarianceClosure",
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
                ("review_notes", models.TextField(blank=True)),
                ("closed_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="CorrectiveAction",
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
                ("cause", models.CharField(max_length=255)),
                ("action", models.TextField()),
                ("due_date", models.DateField()),
                ("evidence", models.TextField(blank=True)),
                ("accountability_acknowledged", models.BooleanField(default=False)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="approved_corrective_actions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "line",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="corrective_action",
                        to="inventory.inventorycountline",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="corrective_actions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="InventoryPlan",
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
                ("title", models.CharField(max_length=255)),
                ("region", models.CharField(max_length=120)),
                ("asset_type", models.CharField(max_length=120)),
                (
                    "mode",
                    models.CharField(
                        choices=[("spot", "Spot Count"), ("full", "Full Count")],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("in_progress", "In Progress"),
                            ("review", "Review"),
                            ("closed", "Closed"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inventory_plans",
                        to="organizations.organization",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="InventoryTask",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("assigned", "Assigned"),
                            ("in_progress", "In Progress"),
                            ("review", "Review"),
                            ("done", "Done"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "assignee",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="inventory_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
