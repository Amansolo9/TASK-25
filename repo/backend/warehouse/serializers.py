from rest_framework import serializers

from warehouse.models import Location, PartnerRecord, Warehouse, Zone


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "name", "region", "is_active", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = [
            "id",
            "warehouse",
            "name",
            "temperature_zone",
            "hazmat_class",
            "is_active",
        ]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = [
            "id",
            "zone",
            "code",
            "capacity_limit",
            "capacity_unit",
            "attributes_json",
            "is_active",
        ]


class PartnerRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerRecord
        fields = [
            "id",
            "partner_type",
            "external_code",
            "display_name",
            "effective_start",
            "effective_end",
            "data_json",
            "created_at",
        ]
        read_only_fields = ["created_at"]
