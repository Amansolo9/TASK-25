from decimal import Decimal

from django.conf import settings
from django.db import models

from organizations.models import Organization
from warehouse.models import Location


class PlanMode(models.TextChoices):
    SPOT = "spot", "Spot Count"
    FULL = "full", "Full Count"


class PlanStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_PROGRESS = "in_progress", "In Progress"
    REVIEW = "review", "Review"
    CLOSED = "closed", "Closed"


class InventoryPlan(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="inventory_plans",
    )
    title = models.CharField(max_length=255)
    region = models.CharField(max_length=120)
    asset_type = models.CharField(max_length=120)
    mode = models.CharField(max_length=20, choices=PlanMode.choices)
    status = models.CharField(
        max_length=20, choices=PlanStatus.choices, default=PlanStatus.DRAFT
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TaskStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ASSIGNED = "assigned", "Assigned"
    IN_PROGRESS = "in_progress", "In Progress"
    REVIEW = "review", "Review"
    DONE = "done", "Done"


class InventoryTask(models.Model):
    plan = models.ForeignKey(
        InventoryPlan, on_delete=models.CASCADE, related_name="tasks"
    )
    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_tasks",
    )
    status = models.CharField(
        max_length=20, choices=TaskStatus.choices, default=TaskStatus.PENDING
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class VarianceType(models.TextChoices):
    MISSING = "missing", "Missing"
    EXTRA = "extra", "Extra"
    DATA_MISMATCH = "data_mismatch", "Data Mismatch"


class InventoryCountLine(models.Model):
    task = models.ForeignKey(
        InventoryTask, on_delete=models.CASCADE, related_name="count_lines"
    )
    asset_code = models.CharField(max_length=120)
    observed_asset_code = models.CharField(max_length=120, blank=True)
    observed_location_code = models.CharField(max_length=120, blank=True)
    attribute_mismatch = models.BooleanField(default=False)
    book_quantity = models.DecimalField(max_digits=14, decimal_places=2)
    physical_quantity = models.DecimalField(max_digits=14, decimal_places=2)
    variance_quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    variance_percent = models.DecimalField(max_digits=9, decimal_places=4, default=0)
    variance_type = models.CharField(
        max_length=20, choices=VarianceType.choices, blank=True
    )
    requires_review = models.BooleanField(default=False)
    closed = models.BooleanField(default=False)

    def calculate_variance(self):
        variance = self.physical_quantity - self.book_quantity
        self.variance_quantity = variance
        if self.book_quantity == 0:
            self.variance_percent = Decimal("1") if variance != 0 else Decimal("0")
        else:
            self.variance_percent = abs(variance) / abs(self.book_quantity)

        has_identifier_mismatch = bool(
            self.attribute_mismatch
            or (
                self.observed_asset_code
                and self.observed_asset_code.strip() != self.asset_code
            )
            or (
                self.observed_location_code
                and self.observed_location_code.strip() != self.task.location.code
            )
        )

        if has_identifier_mismatch:
            self.variance_type = VarianceType.DATA_MISMATCH
        elif variance < 0:
            self.variance_type = VarianceType.MISSING
        elif variance > 0:
            self.variance_type = VarianceType.EXTRA
        else:
            self.variance_type = ""

        threshold_units = Decimal("2")
        threshold_percent = Decimal("0.01")
        self.requires_review = has_identifier_mismatch or abs(variance) > max(
            threshold_units,
            abs(self.book_quantity) * threshold_percent,
        )


class CorrectiveAction(models.Model):
    line = models.OneToOneField(
        InventoryCountLine,
        on_delete=models.CASCADE,
        related_name="corrective_action",
    )
    cause = models.CharField(max_length=255)
    action = models.TextField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="corrective_actions",
    )
    due_date = models.DateField()
    evidence = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_corrective_actions",
    )
    accountability_acknowledged = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)


class VarianceClosure(models.Model):
    line = models.OneToOneField(
        InventoryCountLine,
        on_delete=models.CASCADE,
        related_name="variance_closure",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="variance_closures",
    )
    review_notes = models.TextField(blank=True)
    closed_at = models.DateTimeField(auto_now_add=True)
