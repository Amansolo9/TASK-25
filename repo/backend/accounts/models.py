import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from access.models import Role
from core.crypto import decrypt_text, encrypt_text
from core.masking import mask_last4
from organizations.models import Organization


class User(AbstractUser):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )
    real_name = models.CharField(max_length=255)
    is_verified_identity = models.BooleanField(default=False)
    must_reset_password = models.BooleanField(default=False)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    def is_locked(self):
        return self.locked_until is not None and self.locked_until > timezone.now()


class UserRole(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_roles",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="uniq_user_role")
        ]


class PasswordHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_history",
    )
    password_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)


class CaptchaChallenge(models.Model):
    challenge_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    username = models.CharField(max_length=150)
    prompt = models.CharField(max_length=255)
    answer = models.CharField(max_length=32)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class VerificationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_requests",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    is_high_risk = models.BooleanField(default=False)
    attestation = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)


class VerificationDocument(models.Model):
    class DocumentType(models.TextChoices):
        GOVERNMENT_ID = "government_id", "Government ID"
        CREDENTIAL = "credential", "Credential"
        OTHER = "other", "Other"

    verification_request = models.ForeignKey(
        VerificationRequest,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=40, choices=DocumentType.choices)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    secure_storage_ref = models.CharField(max_length=500, blank=True)
    uploaded_file = models.FileField(upload_to="verification_docs/%Y/%m/%d", blank=True)
    mime_type = models.CharField(max_length=100)
    file_size_bytes = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)


class VerificationReview(models.Model):
    verification_request = models.ForeignKey(
        VerificationRequest,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    approved = models.BooleanField()
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["verification_request", "reviewer"],
                name="uniq_verification_review_per_reviewer",
            )
        ]


class UserPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    locale = models.CharField(max_length=20, default="en")
    timezone = models.CharField(max_length=64, default="UTC")
    large_text_mode = models.BooleanField(default=False)
    high_contrast_mode = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TravelerProfile(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="traveler_profiles",
    )
    display_name = models.CharField(max_length=120)
    encrypted_identifier = models.TextField(blank=True)
    encrypted_government_id = models.TextField(blank=True)
    encrypted_credential_number = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_identifier(self, value):
        self.encrypted_identifier = encrypt_text(value)

    def get_identifier(self):
        return decrypt_text(self.encrypted_identifier)

    def set_government_id(self, value):
        self.encrypted_government_id = encrypt_text(value)

    def get_government_id(self):
        return decrypt_text(self.encrypted_government_id)

    def set_credential_number(self, value):
        self.encrypted_credential_number = encrypt_text(value)

    def get_credential_number(self):
        return decrypt_text(self.encrypted_credential_number)

    @property
    def masked_identifier(self):
        return mask_last4(self.get_identifier())

    @property
    def masked_government_id(self):
        return mask_last4(self.get_government_id())

    @property
    def masked_credential_number(self):
        return mask_last4(self.get_credential_number())


class FavoriteItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_items",
    )
    kind = models.CharField(max_length=40)
    reference_id = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "kind", "reference_id"], name="uniq_user_favorite"
            )
        ]


class ComparisonItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comparison_items",
    )
    kind = models.CharField(max_length=40)
    reference_id = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "kind", "reference_id"],
                name="uniq_user_comparison",
            )
        ]


class LocalSubscriptionAlert(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="local_alerts",
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    acknowledged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class DataExportRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="data_export_requests",
    )
    include_unmasked = models.BooleanField(default=False)
    justification = models.CharField(max_length=255, blank=True)
    format = models.CharField(max_length=10, default="json")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    file_path = models.CharField(max_length=500, blank=True)
    file_size_bytes = models.PositiveIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AccountDeletionRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="deletion_requests",
    )
    retention_notice = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
