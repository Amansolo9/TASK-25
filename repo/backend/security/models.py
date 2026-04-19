from django.conf import settings
from django.db import models

from organizations.models import Organization


class ApiClientKey(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="api_client_keys",
    )
    key_id = models.CharField(max_length=80, unique=True)
    secret_encrypted = models.TextField(blank=True)
    secret_fingerprint = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ReplayNonce(models.Model):
    key_id = models.CharField(max_length=80)
    nonce = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["key_id", "nonce"], name="uniq_key_nonce")
        ]


class UnmaskAccessSession(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="unmask_sessions",
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=120)
    reason = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
