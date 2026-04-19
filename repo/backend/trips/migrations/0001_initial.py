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
            name="Trip",
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
                ("origin", models.CharField(max_length=255)),
                ("destination", models.CharField(max_length=255)),
                ("service_date", models.DateField()),
                ("pickup_window_start", models.DateTimeField()),
                ("pickup_window_end", models.DateTimeField()),
                ("timezone_id", models.CharField(default="UTC", max_length=64)),
                ("signup_deadline", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("live", "Live"),
                            ("unpublished", "Unpublished"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("capacity_limit", models.PositiveIntegerField()),
                (
                    "pricing_model",
                    models.CharField(
                        choices=[("flat", "Flat Fare"), ("per_seat", "Per Seat")],
                        max_length=20,
                    ),
                ),
                ("fare_cents", models.PositiveIntegerField(default=0)),
                ("tax_bps", models.PositiveIntegerField(default=0)),
                ("fee_cents", models.PositiveIntegerField(default=0)),
                ("current_version", models.PositiveIntegerField(default=1)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_trips",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trips",
                        to="organizations.organization",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="updated_trips",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TripWaypoint",
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
                ("sequence", models.PositiveIntegerField()),
                ("name", models.CharField(max_length=255)),
                ("address", models.CharField(blank=True, max_length=255)),
                (
                    "trip",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="waypoints",
                        to="trips.trip",
                    ),
                ),
            ],
            options={"ordering": ["sequence"]},
        ),
        migrations.CreateModel(
            name="TripVersion",
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
                ("version_number", models.PositiveIntegerField()),
                ("change_summary", models.CharField(blank=True, max_length=255)),
                ("material_change", models.BooleanField(default=False)),
                ("snapshot_json", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "changed_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "trip",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="versions",
                        to="trips.trip",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Booking",
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
                            ("confirmed", "Confirmed"),
                            ("waitlisted", "Waitlisted"),
                            ("cancelled", "Cancelled"),
                            ("no_show", "No Show"),
                        ],
                        default="confirmed",
                        max_length=20,
                    ),
                ),
                ("care_priority", models.PositiveIntegerField(default=0)),
                ("acknowledged_version", models.PositiveIntegerField(default=1)),
                ("reack_required", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "rider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "trip",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bookings",
                        to="trips.trip",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="tripwaypoint",
            constraint=models.UniqueConstraint(
                fields=("trip", "sequence"), name="uniq_trip_waypoint_sequence"
            ),
        ),
        migrations.AddConstraint(
            model_name="tripversion",
            constraint=models.UniqueConstraint(
                fields=("trip", "version_number"), name="uniq_trip_version_number"
            ),
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.UniqueConstraint(
                fields=("trip", "rider"), name="uniq_trip_rider_booking"
            ),
        ),
    ]
