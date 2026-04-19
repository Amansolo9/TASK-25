from typing import Any
from pathlib import Path

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.conf import settings
from django.http import FileResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import (
    AccountDeletionRequestSerializer,
    ChangePasswordSerializer,
    ComparisonItemSerializer,
    DataExportRequestSerializer,
    FavoriteItemSerializer,
    LoginSerializer,
    LocalSubscriptionAlertSerializer,
    RegisterSerializer,
    TravelerProfileSerializer,
    VerificationDocumentSerializer,
    VerificationRequestSerializer,
    VerificationReviewSerializer,
    UserPreferenceSerializer,
    UserSerializer,
)
from accounts.models import DataExportRequest, UserPreference, VerificationDocument
from accounts.models import ComparisonItem, FavoriteItem, LocalSubscriptionAlert
from accounts.models import VerificationRequest, VerificationReview
from access.services import is_platform_admin, user_has_permission
from accounts.export_services import process_pending_export_request
from accounts.services import (
    create_captcha_challenge,
    register_login_failure,
    requires_captcha,
    reset_login_failures,
    save_password_history,
    validate_not_recent_password,
    verify_captcha,
)
from audit.services import record_audit_event

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        record_audit_event(
            event_type="auth.register",
            request=request,
            actor=user,
            organization=user.organization,
            resource_type="user",
            resource_id=str(user.id),
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class CaptchaChallengeView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        if not username:
            return Response({"detail": "username is required"}, status=400)

        challenge = create_captcha_challenge(username=username)
        return Response(
            {
                "challenge_id": str(challenge.challenge_id),
                "prompt": challenge.prompt,
                "expires_at": challenge.expires_at,
            }
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope_name = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = User.objects.filter(username=username).first()
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=400)

        if user.is_locked():
            return Response(
                {
                    "detail": "Account is locked.",
                    "locked_until": user.locked_until,
                },
                status=423,
            )

        if requires_captcha(user):
            challenge_id = serializer.validated_data.get("captcha_challenge_id")
            captcha_response = serializer.validated_data.get("captcha_response")
            if not challenge_id or not verify_captcha(
                username, challenge_id, captcha_response
            ):
                return Response(
                    {
                        "detail": "CAPTCHA required or invalid.",
                        "requires_captcha": True,
                    },
                    status=400,
                )

        authed_user = authenticate(
            request=request, username=username, password=password
        )
        if authed_user is None:
            register_login_failure(user)
            record_audit_event(
                event_type="auth.login.failed",
                request=request,
                actor=user,
                organization=user.organization,
                resource_type="user",
                resource_id=str(user.id),
                metadata={"failed_login_attempts": user.failed_login_attempts},
            )
            payload: dict[str, Any] = {"detail": "Invalid credentials."}
            if requires_captcha(user):
                payload["requires_captcha"] = True
            if user.locked_until and user.locked_until > timezone.now():
                payload["locked_until"] = user.locked_until
            return Response(payload, status=400)

        reset_login_failures(authed_user)
        login(request, authed_user)
        record_audit_event(
            event_type="auth.login.success",
            request=request,
            actor=authed_user,
            organization=authed_user.organization,
            resource_type="user",
            resource_id=str(authed_user.id),
        )
        return Response(UserSerializer(authed_user).data)


class LogoutView(APIView):
    def post(self, request):
        record_audit_event(
            event_type="auth.logout",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="user",
            resource_id=str(request.user.id),
        )
        logout(request)
        return Response(status=204)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        new_password = serializer.validated_data["new_password"]
        user = request.user
        if not validate_not_recent_password(user, new_password):
            return Response(
                {"detail": "Password was used recently. Choose a different password."},
                status=400,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])
        save_password_history(user)

        record_audit_event(
            event_type="auth.password.changed",
            request=request,
            actor=user,
            organization=user.organization,
            resource_type="user",
            resource_id=str(user.id),
        )

        return Response({"detail": "Password updated."})


class PreferenceView(APIView):
    def get(self, request):
        pref, _ = UserPreference.objects.get_or_create(user=request.user)
        return Response(UserPreferenceSerializer(pref).data)

    def put(self, request):
        pref, _ = UserPreference.objects.get_or_create(user=request.user)
        serializer = UserPreferenceSerializer(pref, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class TravelerProfileListCreateView(APIView):
    def get(self, request):
        queryset = request.user.traveler_profiles.order_by("-created_at")
        return Response(TravelerProfileSerializer(queryset, many=True).data)

    def post(self, request):
        payload = dict(request.data)
        payload["user"] = request.user.id
        serializer = TravelerProfileSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(user=request.user)
        record_audit_event(
            event_type="profile.traveler.created",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="traveler_profile",
            resource_id=str(profile.id),
        )
        return Response(TravelerProfileSerializer(profile).data, status=201)


class TravelerProfileDetailView(APIView):
    def put(self, request, profile_id):
        profile = request.user.traveler_profiles.filter(id=profile_id).first()
        if not profile:
            return Response({"detail": "Traveler profile not found"}, status=404)
        serializer = TravelerProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class LocalAlertListView(APIView):
    def get(self, request):
        queryset = request.user.local_alerts.order_by("-created_at")
        return Response(LocalSubscriptionAlertSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = LocalSubscriptionAlertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alert = serializer.save(user=request.user)
        return Response(LocalSubscriptionAlertSerializer(alert).data, status=201)


class LocalAlertAcknowledgeView(APIView):
    def post(self, request, alert_id):
        alert = LocalSubscriptionAlert.objects.filter(
            id=alert_id, user=request.user
        ).first()
        if not alert:
            return Response({"detail": "Alert not found"}, status=404)
        alert.acknowledged = True
        alert.save(update_fields=["acknowledged"])
        return Response(LocalSubscriptionAlertSerializer(alert).data)


class FavoriteItemListCreateView(APIView):
    def get(self, request):
        queryset = FavoriteItem.objects.filter(user=request.user).order_by(
            "-created_at"
        )
        return Response(FavoriteItemSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = FavoriteItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj, created = FavoriteItem.objects.get_or_create(
            user=request.user,
            kind=serializer.validated_data["kind"],
            reference_id=serializer.validated_data["reference_id"],
        )
        if not created:
            return Response(
                {
                    "detail": "Favorite already exists",
                    "code": "favorite_conflict",
                },
                status=409,
            )
        return Response(FavoriteItemSerializer(obj).data, status=201)


class FavoriteItemDeleteView(APIView):
    def delete(self, request, favorite_id):
        deleted, _ = FavoriteItem.objects.filter(
            id=favorite_id, user=request.user
        ).delete()
        if not deleted:
            return Response({"detail": "Favorite not found"}, status=404)
        return Response(status=204)


class ComparisonItemListCreateView(APIView):
    def get(self, request):
        queryset = ComparisonItem.objects.filter(user=request.user).order_by(
            "-created_at"
        )
        return Response(ComparisonItemSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = ComparisonItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj, created = ComparisonItem.objects.get_or_create(
            user=request.user,
            kind=serializer.validated_data["kind"],
            reference_id=serializer.validated_data["reference_id"],
        )
        if not created:
            return Response(
                {
                    "detail": "Comparison item already exists",
                    "code": "comparison_conflict",
                },
                status=409,
            )
        return Response(ComparisonItemSerializer(obj).data, status=201)


class ComparisonItemDeleteView(APIView):
    def delete(self, request, comparison_id):
        deleted, _ = ComparisonItem.objects.filter(
            id=comparison_id, user=request.user
        ).delete()
        if not deleted:
            return Response({"detail": "Comparison item not found"}, status=404)
        return Response(status=204)


class ExportRequestCreateView(APIView):
    def post(self, request):
        serializer = DataExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        include_unmasked = serializer.validated_data.get("include_unmasked", False)
        if include_unmasked and not serializer.validated_data.get("justification"):
            return Response(
                {"detail": "Justification is required for unmasked export."}, status=400
            )

        if include_unmasked and not user_has_permission(
            request.user, "sensitive.unmask"
        ):
            return Response(
                {"detail": "Missing permission: sensitive.unmask for unmasked export."},
                status=403,
            )

        req = serializer.save(user=request.user)
        record_audit_event(
            event_type=(
                "export.unmasked.requested" if include_unmasked else "export.requested"
            ),
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="data_export",
            resource_id=str(req.id),
            metadata={
                "justification": serializer.validated_data.get("justification", ""),
                "format": serializer.validated_data.get("format", "json"),
            },
        )
        return Response(DataExportRequestSerializer(req).data, status=201)


class ExportRequestListView(APIView):
    def get(self, request):
        queryset = DataExportRequest.objects.filter(user=request.user).order_by(
            "-created_at"
        )
        return Response(DataExportRequestSerializer(queryset, many=True).data)


class ExportRequestDownloadView(APIView):
    def get(self, request, export_id):
        export_request = DataExportRequest.objects.filter(id=export_id).first()
        if not export_request:
            return Response({"detail": "Export request not found"}, status=404)

        is_owner = export_request.user_id == request.user.id
        has_privileged_download = user_has_permission(request.user, "export.read.any")
        if not is_owner and not has_privileged_download:
            return Response(
                {"detail": "Not authorized to access this export"}, status=403
            )

        if (
            not is_owner
            and not is_platform_admin(request.user)
            and export_request.user.organization_id != request.user.organization_id
        ):
            return Response({"detail": "Export request not found"}, status=404)

        if export_request.status == DataExportRequest.Status.PENDING:
            export_request = process_pending_export_request(export_request)

        if export_request.status != DataExportRequest.Status.READY:
            return Response(
                {
                    "detail": "Export is not available for download",
                    "status": export_request.status,
                },
                status=409,
            )

        file_ref = Path(settings.BASE_DIR) / export_request.file_path
        if not file_ref.exists():
            return Response({"detail": "Export artifact not found"}, status=404)

        record_audit_event(
            event_type="export.downloaded",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="data_export",
            resource_id=str(export_request.id),
            metadata={"owner_user_id": export_request.user_id},
        )
        return FileResponse(
            file_ref.open("rb"),
            as_attachment=True,
            filename=file_ref.name,
            content_type=(
                "text/csv" if file_ref.suffix.lower() == ".csv" else "application/json"
            ),
        )


class AccountDeletionRequestView(APIView):
    def post(self, request):
        serializer = AccountDeletionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = serializer.save(user=request.user)
        request.user.is_active = False
        request.user.save(update_fields=["is_active"])
        record_audit_event(
            event_type="account.deletion.requested",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="account_deletion",
            resource_id=str(req.id),
        )
        return Response(AccountDeletionRequestSerializer(req).data, status=201)


class VerificationRequestListCreateView(APIView):
    def get(self, request):
        if user_has_permission(request.user, "verification.review"):
            queryset = VerificationRequest.objects.filter(
                user__organization=request.user.organization
            ).order_by("-submitted_at")
        else:
            queryset = VerificationRequest.objects.filter(user=request.user).order_by(
                "-submitted_at"
            )
        return Response(VerificationRequestSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = VerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = serializer.save(user=request.user)
        return Response(VerificationRequestSerializer(req).data, status=201)


class VerificationReviewCreateView(APIView):
    def post(self, request, verification_id):
        if not user_has_permission(request.user, "verification.review"):
            return Response(
                {"detail": "Missing permission: verification.review"}, status=403
            )

        verification = VerificationRequest.objects.filter(
            id=verification_id,
            user__organization=request.user.organization,
        ).first()
        if not verification:
            return Response({"detail": "Verification request not found"}, status=404)

        serializer = VerificationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if verification.reviews.filter(reviewer=request.user).exists():
            return Response(
                {
                    "detail": "Reviewer has already submitted a review for this request.",
                    "code": "duplicate_reviewer",
                },
                status=409,
            )
        review = VerificationReview.objects.create(
            verification_request=verification,
            reviewer=request.user,
            approved=serializer.validated_data["approved"],
            comments=serializer.validated_data.get("comments", ""),
        )

        approvals = (
            verification.reviews.filter(approved=True)
            .values("reviewer_id")
            .distinct()
            .count()
        )
        needed_approvals = 2 if verification.is_high_risk else 1
        if approvals >= needed_approvals:
            verification.status = "approved"
            verification.reviewed_at = timezone.now()
            verification.user.is_verified_identity = True
            verification.user.save(update_fields=["is_verified_identity"])
            verification.save(update_fields=["status", "reviewed_at"])
        elif verification.reviews.filter(approved=False).exists():
            verification.status = "rejected"
            verification.reviewed_at = timezone.now()
            verification.save(update_fields=["status", "reviewed_at"])

        record_audit_event(
            event_type="verification.reviewed",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="verification_request",
            resource_id=str(verification.id),
            metadata={
                "approved": review.approved,
                "high_risk": verification.is_high_risk,
            },
        )
        return Response(VerificationReviewSerializer(review).data, status=201)


class VerificationDocumentUploadView(APIView):
    def post(self, request, verification_id):
        verification = VerificationRequest.objects.filter(
            id=verification_id,
            user=request.user,
        ).first()
        if not verification:
            return Response({"detail": "Verification request not found"}, status=404)

        serializer = VerificationDocumentSerializer(
            data={
                "document_type": request.data.get("document_type"),
                "file_name": request.data.get("file_name", ""),
                "file_path": request.data.get("file_path", ""),
                "mime_type": request.data.get("mime_type", ""),
                "file_size_bytes": request.data.get("file_size_bytes", 0),
                "uploaded_file": request.data.get("uploaded_file"),
            }
        )
        serializer.is_valid(raise_exception=True)

        doc_payload = dict(serializer.validated_data)
        upload = doc_payload.pop("uploaded_file", None)
        doc = VerificationDocument.objects.create(
            verification_request=verification,
            **doc_payload,
        )
        if upload is not None:
            doc.uploaded_file = upload
            doc.save(update_fields=["uploaded_file"])
            doc.secure_storage_ref = doc.uploaded_file.name
            doc.file_path = doc.uploaded_file.name
            doc.save(update_fields=["secure_storage_ref", "file_path"])
        return Response(VerificationRequestSerializer(verification).data, status=201)


class VerificationDocumentOpenView(APIView):
    def get(self, request, document_id):
        doc = (
            VerificationDocument.objects.filter(
                id=document_id,
                verification_request__user__organization=request.user.organization,
            )
            .select_related("verification_request", "verification_request__user")
            .first()
        )
        if not doc:
            return Response({"detail": "Document not found"}, status=404)

        is_owner = doc.verification_request.user_id == request.user.id
        is_reviewer = user_has_permission(request.user, "verification.review")
        if not is_owner and not is_reviewer:
            return Response(
                {"detail": "Not authorized to open this document"}, status=403
            )
        if not doc.uploaded_file:
            return Response({"detail": "Document file is not available"}, status=404)

        return FileResponse(
            doc.uploaded_file.open("rb"),
            content_type=doc.mime_type,
            filename=doc.file_name,
            as_attachment=False,
        )
