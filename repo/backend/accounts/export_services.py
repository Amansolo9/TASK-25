import csv
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import (
    ComparisonItem,
    DataExportRequest,
    FavoriteItem,
    LocalSubscriptionAlert,
    TravelerProfile,
    UserPreference,
    VerificationDocument,
    VerificationRequest,
)
from audit.services import record_audit_event


def _export_dir():
    target = Path(settings.MEDIA_ROOT) / "exports"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _serialize_user_scope(export_request):
    user = export_request.user
    profile = UserPreference.objects.filter(user=user).first()
    verification_requests = list(
        VerificationRequest.objects.filter(user=user).order_by("-submitted_at")
    )
    verification_ids = [item.id for item in verification_requests]
    verification_documents = list(
        VerificationDocument.objects.filter(
            verification_request_id__in=verification_ids
        )
        .order_by("-uploaded_at")
        .values(
            "id",
            "verification_request_id",
            "document_type",
            "file_name",
            "mime_type",
            "file_size_bytes",
            "uploaded_at",
        )
    )

    return {
        "generated_at": timezone.now().isoformat(),
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "organization_id": user.organization_id,
            "is_verified_identity": user.is_verified_identity,
        },
        "preference": {
            "locale": getattr(profile, "locale", ""),
            "timezone": getattr(profile, "timezone", ""),
            "large_text_mode": getattr(profile, "large_text_mode", False),
            "high_contrast_mode": getattr(profile, "high_contrast_mode", False),
        },
        "favorites": list(
            FavoriteItem.objects.filter(user=user)
            .order_by("-created_at")
            .values("id", "kind", "reference_id", "created_at")
        ),
        "comparisons": list(
            ComparisonItem.objects.filter(user=user)
            .order_by("-created_at")
            .values("id", "kind", "reference_id", "created_at")
        ),
        "alerts": list(
            LocalSubscriptionAlert.objects.filter(user=user)
            .order_by("-created_at")
            .values("id", "title", "message", "acknowledged", "created_at")
        ),
        "traveler_profiles": list(
            TravelerProfile.objects.filter(user=user)
            .order_by("-created_at")
            .values(
                "id",
                "display_name",
                "encrypted_identifier",
                "encrypted_government_id",
                "encrypted_credential_number",
                "created_at",
            )
        ),
        "verification_requests": [
            {
                "id": item.id,
                "status": item.status,
                "is_high_risk": item.is_high_risk,
                "attestation": item.attestation,
                "submitted_at": item.submitted_at.isoformat(),
                "reviewed_at": item.reviewed_at.isoformat()
                if item.reviewed_at
                else None,
            }
            for item in verification_requests
        ],
        "verification_documents": verification_documents,
    }


def _write_json(file_path, payload):
    data = json.dumps(payload, indent=2, sort_keys=True, default=str).encode("utf-8")
    file_path.write_bytes(data)
    return data


def _write_csv(file_path, payload):
    with file_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["section", "payload_json"])
        for key, value in payload.items():
            writer.writerow([key, json.dumps(value, default=str, sort_keys=True)])
    return file_path.read_bytes()


@transaction.atomic
def process_pending_export_request(export_request):
    if export_request.status != DataExportRequest.Status.PENDING:
        return export_request

    try:
        if export_request.format not in {"json", "csv"}:
            raise ValueError("Unsupported export format")

        payload = _serialize_user_scope(export_request)
        extension = export_request.format
        filename = f"export_{export_request.user_id}_{export_request.id}.{extension}"
        target = _export_dir() / filename
        raw = (
            _write_csv(target, payload)
            if extension == "csv"
            else _write_json(target, payload)
        )

        export_request.file_path = str(target.relative_to(settings.BASE_DIR))
        export_request.file_size_bytes = len(raw)
        export_request.checksum_sha256 = hashlib.sha256(raw).hexdigest()
        export_request.status = DataExportRequest.Status.READY
        export_request.failure_reason = ""
        export_request.processed_at = timezone.now()
        export_request.save(
            update_fields=[
                "file_path",
                "file_size_bytes",
                "checksum_sha256",
                "status",
                "failure_reason",
                "processed_at",
            ]
        )
        record_audit_event(
            event_type="export.ready",
            actor=export_request.user,
            organization=export_request.user.organization,
            resource_type="data_export",
            resource_id=str(export_request.id),
            metadata={"file_path": export_request.file_path},
        )
    except Exception as exc:  # pragma: no cover - defensive
        export_request.status = DataExportRequest.Status.FAILED
        export_request.failure_reason = str(exc)[:255]
        export_request.processed_at = timezone.now()
        export_request.save(update_fields=["status", "failure_reason", "processed_at"])
        record_audit_event(
            event_type="export.failed",
            actor=export_request.user,
            organization=export_request.user.organization,
            resource_type="data_export",
            resource_id=str(export_request.id),
            metadata={"error": export_request.failure_reason},
        )

    return export_request


def process_pending_exports(limit=50):
    queryset = DataExportRequest.objects.select_related(
        "user", "user__organization"
    ).filter(status=DataExportRequest.Status.PENDING)
    if limit:
        queryset = queryset.order_by("created_at")[:limit]
    for item in queryset:
        process_pending_export_request(item)
