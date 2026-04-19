from django.conf import settings
from django.db import models


class IdempotencyRecord(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="idempotency_records",
        null=True,
        blank=True,
    )
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255)
    key = models.CharField(max_length=128)
    status_code = models.PositiveSmallIntegerField()
    response_body = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "method", "path", "key"],
                name="uniq_idempotency_request",
            )
        ]
        indexes = [
            models.Index(fields=["created_at"], name="core_idempotency_created_idx")
        ]
