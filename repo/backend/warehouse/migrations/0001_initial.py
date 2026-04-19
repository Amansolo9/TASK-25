import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Warehouse",
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
                ("name", models.CharField(max_length=255)),
                ("region", models.CharField(max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="warehouses",
                        to="organizations.organization",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Zone",
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
                ("name", models.CharField(max_length=120)),
                ("temperature_zone", models.CharField(blank=True, max_length=80)),
                ("hazmat_class", models.CharField(blank=True, max_length=80)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "warehouse",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="zones",
                        to="warehouse.warehouse",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Location",
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
                ("code", models.CharField(max_length=80)),
                (
                    "capacity_limit",
                    models.DecimalField(decimal_places=2, max_digits=12),
                ),
                ("capacity_unit", models.CharField(default="units", max_length=30)),
                ("attributes_json", models.JSONField(default=dict)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "zone",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="locations",
                        to="warehouse.zone",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PartnerRecord",
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
                    "partner_type",
                    models.CharField(
                        choices=[
                            ("owner", "Owner"),
                            ("supplier", "Supplier"),
                            ("carrier", "Carrier"),
                        ],
                        max_length=20,
                    ),
                ),
                ("external_code", models.CharField(max_length=80)),
                ("display_name", models.CharField(max_length=255)),
                ("effective_start", models.DateField()),
                ("effective_end", models.DateField(blank=True, null=True)),
                ("data_json", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="partner_records",
                        to="organizations.organization",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="warehouse",
            constraint=models.UniqueConstraint(
                fields=("organization", "name"), name="uniq_org_warehouse_name"
            ),
        ),
        migrations.AddConstraint(
            model_name="zone",
            constraint=models.UniqueConstraint(
                fields=("warehouse", "name"), name="uniq_warehouse_zone"
            ),
        ),
        migrations.AddConstraint(
            model_name="location",
            constraint=models.UniqueConstraint(
                fields=("zone", "code"), name="uniq_zone_location_code"
            ),
        ),
        migrations.AddIndex(
            model_name="partnerrecord",
            index=models.Index(
                fields=["organization", "partner_type", "external_code"],
                name="warehouse_partner_lookup_idx",
            ),
        ),
    ]
