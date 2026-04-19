from rest_framework import serializers

from security.models import UnmaskAccessSession


class UnmaskAccessSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnmaskAccessSession
        fields = ["id", "field_name", "reason", "expires_at", "created_at"]
        read_only_fields = ["expires_at", "created_at"]
