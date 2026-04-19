from rest_framework import serializers

from access.models import Permission, Role


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["code", "screen", "action", "description"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ["id", "code", "name", "is_base_role", "permissions"]

    def get_permissions(self, obj):
        permissions = [
            rp.permission for rp in obj.role_permissions.select_related("permission")
        ]
        return PermissionSerializer(permissions, many=True).data
