from rest_framework import serializers

from monitoring.models import AlertThreshold, AnomalyAlert


class AnomalyAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnomalyAlert
        fields = [
            "id",
            "alert_type",
            "severity",
            "title",
            "details",
            "metadata_json",
            "acknowledged",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class AlertThresholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertThreshold
        fields = [
            "id",
            "alert_type",
            "numeric_threshold",
            "window_minutes",
            "created_at",
        ]
        read_only_fields = ["created_at"]
