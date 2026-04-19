from rest_framework import serializers

from inventory.models import (
    CorrectiveAction,
    InventoryCountLine,
    InventoryPlan,
    InventoryTask,
    VarianceClosure,
)


class InventoryPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryPlan
        fields = [
            "id",
            "title",
            "region",
            "asset_type",
            "mode",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "created_at", "updated_at"]


class InventoryTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryTask
        fields = [
            "id",
            "plan",
            "location",
            "assignee",
            "status",
            "started_at",
            "completed_at",
        ]


class InventoryCountLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryCountLine
        fields = [
            "id",
            "task",
            "asset_code",
            "observed_asset_code",
            "observed_location_code",
            "attribute_mismatch",
            "book_quantity",
            "physical_quantity",
            "variance_quantity",
            "variance_percent",
            "variance_type",
            "requires_review",
            "closed",
        ]
        read_only_fields = [
            "variance_quantity",
            "variance_percent",
            "variance_type",
            "requires_review",
            "closed",
        ]


class CorrectiveActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectiveAction
        fields = [
            "id",
            "line",
            "cause",
            "action",
            "owner",
            "due_date",
            "evidence",
            "approved_by",
            "accountability_acknowledged",
            "approved_at",
        ]
        read_only_fields = ["approved_by", "approved_at"]


class VarianceClosureSerializer(serializers.ModelSerializer):
    class Meta:
        model = VarianceClosure
        fields = ["id", "line", "reviewer", "review_notes", "closed_at"]
        read_only_fields = ["closed_at"]
