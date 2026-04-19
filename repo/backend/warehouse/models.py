from datetime import date

from django.core.exceptions import ValidationError
from django.db import models

from organizations.models import Organization


class Warehouse(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="warehouses",
    )
    name = models.CharField(max_length=255)
    region = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"], name="uniq_org_warehouse_name"
            )
        ]


class Zone(models.Model):
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="zones"
    )
    name = models.CharField(max_length=120)
    temperature_zone = models.CharField(max_length=80, blank=True)
    hazmat_class = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "name"], name="uniq_warehouse_zone"
            )
        ]


class Location(models.Model):
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="locations")
    code = models.CharField(max_length=80)
    capacity_limit = models.DecimalField(max_digits=12, decimal_places=2)
    capacity_unit = models.CharField(max_length=30, default="units")
    attributes_json = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "code"], name="uniq_zone_location_code"
            )
        ]


class PartnerType(models.TextChoices):
    OWNER = "owner", "Owner"
    SUPPLIER = "supplier", "Supplier"
    CARRIER = "carrier", "Carrier"


class PartnerRecord(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="partner_records",
    )
    partner_type = models.CharField(max_length=20, choices=PartnerType.choices)
    external_code = models.CharField(max_length=80)
    display_name = models.CharField(max_length=255)
    effective_start = models.DateField()
    effective_end = models.DateField(null=True, blank=True)
    data_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["organization", "partner_type", "external_code"],
                name="warehouse_partner_lookup_idx",
            )
        ]

    def clean(self):
        if self.effective_end and self.effective_end < self.effective_start:
            raise ValidationError("effective_end must be on or after effective_start")

        overlap_qs = PartnerRecord.objects.filter(
            organization=self.organization,
            partner_type=self.partner_type,
            external_code=self.external_code,
        ).exclude(id=self.id)

        for other in overlap_qs:
            other_end = other.effective_end or date.max
            this_end = self.effective_end or date.max
            if self.effective_start <= other_end and other.effective_start <= this_end:
                raise ValidationError(
                    "Overlapping effective date ranges are not allowed"
                )
