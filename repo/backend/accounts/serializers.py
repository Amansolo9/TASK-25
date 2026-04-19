from django.contrib.auth import get_user_model, password_validation
from django.db import transaction
from rest_framework import serializers

from access.models import BaseRole, Role
from accounts.models import UserRole
from accounts.models import (
    AccountDeletionRequest,
    ComparisonItem,
    DataExportRequest,
    FavoriteItem,
    LocalSubscriptionAlert,
    VerificationDocument,
    VerificationRequest,
    VerificationReview,
    TravelerProfile,
    UserPreference,
)
from accounts.services import save_password_history, validate_not_recent_password
from organizations.models import Organization

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    organization_code = serializers.CharField(max_length=40)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    real_name = serializers.CharField(max_length=255)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username is already in use.")
        return value

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        organization = Organization.objects.filter(
            code=validated_data["organization_code"], is_active=True
        ).first()
        if organization is None:
            raise serializers.ValidationError(
                {"organization_code": "Invalid organization."}
            )

        user = User(
            organization=organization,
            username=validated_data["username"],
            real_name=validated_data["real_name"],
        )
        user.set_password(validated_data["password"])
        user.full_clean()
        user.save()
        save_password_history(user)

        base_role = Role.objects.filter(
            organization=organization,
            code=BaseRole.SENIOR,
            is_base_role=True,
        ).first()
        if base_role:
            UserRole.objects.create(user=user, role=base_role)

        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    captcha_challenge_id = serializers.UUIDField(required=False)
    captcha_response = serializers.CharField(required=False, allow_blank=True)


class UserSerializer(serializers.ModelSerializer):
    organization_code = serializers.CharField(
        source="organization.code", read_only=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "real_name",
            "organization_code",
            "is_verified_identity",
            "failed_login_attempts",
            "locked_until",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        password_validation.validate_password(value, self.context["request"].user)
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "Invalid current password."}
            )
        if not validate_not_recent_password(user, attrs["new_password"]):
            raise serializers.ValidationError(
                {
                    "new_password": "Password was used recently. Choose a different password."
                }
            )
        return attrs


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = [
            "locale",
            "timezone",
            "large_text_mode",
            "high_contrast_mode",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class TravelerProfileSerializer(serializers.ModelSerializer):
    identifier = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    government_id = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    credential_number = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    masked_identifier = serializers.CharField(read_only=True)
    masked_government_id = serializers.CharField(read_only=True)
    masked_credential_number = serializers.CharField(read_only=True)

    class Meta:
        model = TravelerProfile
        fields = [
            "id",
            "display_name",
            "identifier",
            "government_id",
            "credential_number",
            "masked_identifier",
            "masked_government_id",
            "masked_credential_number",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def create(self, validated_data):
        identifier = validated_data.pop("identifier", "")
        government_id = validated_data.pop("government_id", "")
        credential_number = validated_data.pop("credential_number", "")
        profile = TravelerProfile(**validated_data)
        if identifier:
            profile.set_identifier(identifier)
        if government_id:
            profile.set_government_id(government_id)
        if credential_number:
            profile.set_credential_number(credential_number)
        profile.save()
        return profile

    def update(self, instance, validated_data):
        identifier = validated_data.pop("identifier", None)
        government_id = validated_data.pop("government_id", None)
        credential_number = validated_data.pop("credential_number", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if identifier is not None:
            instance.set_identifier(identifier)
        if government_id is not None:
            instance.set_government_id(government_id)
        if credential_number is not None:
            instance.set_credential_number(credential_number)
        instance.save()
        return instance


class LocalSubscriptionAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalSubscriptionAlert
        fields = ["id", "title", "message", "acknowledged", "created_at"]
        read_only_fields = ["created_at"]


class FavoriteItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteItem
        fields = ["id", "kind", "reference_id", "created_at"]
        read_only_fields = ["created_at"]


class ComparisonItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComparisonItem
        fields = ["id", "kind", "reference_id", "created_at"]
        read_only_fields = ["created_at"]


class DataExportRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataExportRequest
        fields = [
            "id",
            "include_unmasked",
            "justification",
            "format",
            "status",
            "file_path",
            "file_size_bytes",
            "checksum_sha256",
            "failure_reason",
            "processed_at",
            "created_at",
        ]
        read_only_fields = [
            "status",
            "file_path",
            "file_size_bytes",
            "checksum_sha256",
            "failure_reason",
            "processed_at",
            "created_at",
        ]


class AccountDeletionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountDeletionRequest
        fields = ["id", "retention_notice", "status", "requested_at", "completed_at"]
        read_only_fields = ["status", "requested_at", "completed_at"]


class VerificationDocumentSerializer(serializers.ModelSerializer):
    file_name = serializers.CharField(required=False, allow_blank=True)
    file_path = serializers.CharField(required=False, allow_blank=True)
    mime_type = serializers.CharField(required=False, allow_blank=True)
    file_size_bytes = serializers.IntegerField(required=False)
    uploaded_file = serializers.FileField(required=False)

    def validate(self, attrs):
        allowed = {"image/jpeg", "image/png", "application/pdf"}
        upload = attrs.get("uploaded_file")
        mime = attrs.get("mime_type", "")
        size = attrs.get("file_size_bytes", 0)

        if upload is not None:
            mime = getattr(upload, "content_type", "") or mime
            size = int(getattr(upload, "size", 0) or 0)
            attrs["file_name"] = attrs.get("file_name") or getattr(
                upload, "name", "upload"
            )
            attrs["mime_type"] = mime
            attrs["file_size_bytes"] = size

        if mime not in allowed:
            raise serializers.ValidationError(
                {"mime_type": "Allowed types: image/jpeg, image/png, application/pdf"}
            )

        if size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                {"file_size_bytes": "Maximum size is 10 MB"}
            )

        if upload is None and not attrs.get("file_path"):
            raise serializers.ValidationError(
                {
                    "file_path": "file_path is required when uploaded_file is not provided"
                }
            )
        return attrs

    class Meta:
        model = VerificationDocument
        fields = [
            "id",
            "document_type",
            "file_name",
            "file_path",
            "secure_storage_ref",
            "uploaded_file",
            "mime_type",
            "file_size_bytes",
            "uploaded_at",
        ]
        read_only_fields = ["uploaded_at", "secure_storage_ref"]


class VerificationRequestSerializer(serializers.ModelSerializer):
    documents = VerificationDocumentSerializer(many=True, required=False)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    reviewer_approvals = serializers.SerializerMethodField()

    class Meta:
        model = VerificationRequest
        fields = [
            "id",
            "user_id",
            "username",
            "status",
            "is_high_risk",
            "attestation",
            "submitted_at",
            "reviewed_at",
            "documents",
            "reviewer_approvals",
        ]
        read_only_fields = ["status", "submitted_at", "reviewed_at"]

    def create(self, validated_data):
        docs = validated_data.pop("documents", [])
        req = VerificationRequest.objects.create(**validated_data)
        for doc in docs:
            VerificationDocument.objects.create(verification_request=req, **doc)
        return req

    def get_reviewer_approvals(self, obj):
        return obj.reviews.filter(approved=True).count()


class VerificationReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationReview
        fields = ["id", "verification_request", "approved", "comments", "created_at"]
        read_only_fields = ["created_at"]
