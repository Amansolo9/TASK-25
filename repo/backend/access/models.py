from django.db import models

from organizations.models import Organization


class BaseRole(models.TextChoices):
    SENIOR = "senior", "Senior"
    FAMILY_MEMBER = "family_member", "Family Member"
    CAREGIVER = "caregiver", "Caregiver"
    ORG_ADMIN = "org_admin", "Organization Admin"
    PLATFORM_ADMIN = "platform_admin", "Platform Admin"


class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    screen = models.CharField(max_length=100)
    action = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.code


class Role(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="roles",
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=120)
    is_base_role = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="uniq_org_role_code"
            )
        ]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="role_permissions"
    )
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="permission_roles"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"], name="uniq_role_permission"
            )
        ]
