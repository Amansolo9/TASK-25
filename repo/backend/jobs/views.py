from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from access.services import is_platform_admin, user_has_permission
from audit.services import record_audit_event
from core.structured_logging import log_app_event
from organizations.models import Organization
from django.utils import timezone

from jobs.models import (
    IngestAttachmentFingerprint,
    IngestRowError,
    Job,
    JobCheckpoint,
    JobDependency,
)
from jobs.serializers import (
    IngestAttachmentFingerprintSerializer,
    IngestRowErrorResolveSerializer,
    IngestRowErrorSerializer,
    JobCheckpointSerializer,
    JobFailureSerializer,
    JobSerializer,
)
from jobs.services import (
    claim_next_job,
    heartbeat,
    resolve_concurrency_limit,
    require_lease_owner,
    validate_dependency_graph,
)
from jobs.services import mark_job_failure, mark_job_success


def _signed_org_id(request):
    return getattr(request, "signed_organization_id", None)


class JobListCreateView(APIView):
    permission_classes = []

    def get(self, request):
        if not user_has_permission(request.user, "jobs.read"):
            return Response({"detail": "Missing permission: jobs.read"}, status=403)
        queryset = Job.objects.all()
        if is_platform_admin(request.user):
            org_id = request.GET.get("organization_id")
            if org_id:
                queryset = queryset.filter(organization_id=org_id)
        else:
            queryset = queryset.filter(organization=request.user.organization)

        status_filter = (request.GET.get("status") or "").strip().lower()
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        sort_by = (request.GET.get("sort_by") or "created_at").strip()
        sort_order = (request.GET.get("sort_order") or "desc").strip().lower()
        if sort_by not in {"created_at", "priority", "next_run_at"}:
            return Response(
                {"detail": "sort_by must be one of: created_at, priority, next_run_at"},
                status=400,
            )
        if sort_order not in {"asc", "desc"}:
            return Response(
                {"detail": "sort_order must be one of: asc, desc"}, status=400
            )

        limit_raw = request.GET.get("limit")
        offset_raw = request.GET.get("offset", "0")
        try:
            limit = int(limit_raw) if limit_raw is not None else 50
            offset = int(offset_raw)
        except ValueError:
            return Response({"detail": "limit and offset must be integers"}, status=400)
        if limit < 1 or limit > 100:
            return Response({"detail": "limit must be between 1 and 100"}, status=400)
        if offset < 0:
            return Response({"detail": "offset must be >= 0"}, status=400)

        order_field = sort_by if sort_order == "asc" else f"-{sort_by}"
        queryset = queryset.order_by(order_field, "id")[offset : offset + limit]

        return Response(JobSerializer(queryset, many=True).data)

    def post(self, request):
        signed_api_key = getattr(request, "signed_api_key", None)
        signed_org_id = _signed_org_id(request) or getattr(
            signed_api_key, "organization_id", None
        )
        signed_machine_context = bool(
            signed_api_key and not getattr(request.user, "is_authenticated", False)
        )
        if not signed_machine_context and not user_has_permission(
            request.user, "jobs.write"
        ):
            return Response({"detail": "Missing permission: jobs.write"}, status=403)

        serializer = JobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dependency_ids = serializer.validated_data.pop("dependency_ids", [])
        if signed_machine_context and dependency_ids:
            return Response(
                {
                    "detail": "dependency_ids are not supported for signed machine job create"
                },
                status=400,
            )

        dedupe_key = serializer.validated_data.get("dedupe_key", "").strip()
        target_org = None
        if signed_machine_context:
            target_org = Organization.objects.filter(
                id=signed_org_id, is_active=True
            ).first()
        else:
            target_org = request.user.organization
        if (
            not signed_machine_context
            and is_platform_admin(request.user)
            and request.data.get("organization_id")
        ):
            target_org = Organization.objects.filter(
                id=request.data.get("organization_id"), is_active=True
            ).first()
        if target_org is None:
            return Response(
                {"detail": "Valid organization_id is required."}, status=400
            )

        if dedupe_key:
            existing = Job.objects.filter(
                organization=target_org,
                job_type=serializer.validated_data["job_type"],
                dedupe_key=dedupe_key,
                status__in=["pending", "running", "blocked"],
            ).first()
            if existing:
                return Response(JobSerializer(existing).data, status=200)

        created_by = (
            request.user if getattr(request.user, "is_authenticated", False) else None
        )
        obj = serializer.save(organization=target_org, created_by=created_by)
        try:
            validate_dependency_graph(obj, dependency_ids)
        except ValueError as exc:
            obj.delete()
            return Response(
                {"detail": str(exc), "code": "invalid_dependency_graph"}, status=400
            )
        for dep_id in dependency_ids:
            dep = get_object_or_404(
                Job,
                id=dep_id,
                **(
                    {"organization": request.user.organization}
                    if not signed_machine_context
                    and not is_platform_admin(request.user)
                    else (
                        {"organization": target_org} if signed_machine_context else {}
                    )
                ),
            )
            JobDependency.objects.create(job=obj, depends_on=dep)

        if getattr(request.user, "is_authenticated", False):
            record_audit_event(
                event_type="job.created",
                request=request,
                actor=request.user,
                organization=request.user.organization,
                resource_type="job",
                resource_id=str(obj.id),
            )
        return Response(JobSerializer(obj).data, status=status.HTTP_201_CREATED)


class JobRetryView(APIView):
    def post(self, request, job_id):
        if not user_has_permission(request.user, "jobs.write"):
            return Response({"detail": "Missing permission: jobs.write"}, status=403)

        job = get_object_or_404(
            Job,
            id=job_id,
            **(
                {"organization": request.user.organization}
                if not is_platform_admin(request.user)
                else {}
            ),
        )
        job.status = "pending"
        job.save(update_fields=["status"])
        return Response({"detail": "Job re-queued"})


class JobCheckpointUpsertView(APIView):
    def post(self, request, job_id):
        if not user_has_permission(request.user, "jobs.write"):
            return Response({"detail": "Missing permission: jobs.write"}, status=403)
        job = get_object_or_404(
            Job,
            id=job_id,
            **(
                {"organization": request.user.organization}
                if not is_platform_admin(request.user)
                else {}
            ),
        )
        payload = dict(request.data)
        payload["job"] = job.id
        serializer = JobCheckpointSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        cp, _ = JobCheckpoint.objects.update_or_create(
            job=job,
            file_name=serializer.validated_data["file_name"],
            defaults={
                "row_offset": serializer.validated_data["row_offset"],
                "attachment_index": serializer.validated_data["attachment_index"],
                "state_json": serializer.validated_data["state_json"],
            },
        )
        return Response(JobCheckpointSerializer(cp).data)


class JobClaimView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        worker_id = request.data.get("worker_id")
        org_id = _signed_org_id(request)
        if not org_id:
            log_app_event(
                "jobs", "worker.claim.unauthorized", reason="missing_signed_org"
            )
            return Response(
                {"detail": "Signed organization context required"}, status=401
            )
        if not worker_id:
            log_app_event(
                "jobs", "worker.claim.bad_request", reason="missing_worker_id"
            )
            return Response({"detail": "worker_id is required"}, status=400)

        requested_org_id = request.data.get("organization_id")
        if requested_org_id:
            try:
                if int(requested_org_id) != int(org_id):
                    return Response(
                        {"detail": "organization_id does not match signed key context"},
                        status=403,
                    )
            except (TypeError, ValueError):
                return Response(
                    {"detail": "organization_id must be numeric"}, status=400
                )

        job = claim_next_job(
            worker_id=worker_id,
            organization_id=org_id,
            concurrency_limit=resolve_concurrency_limit(),
        )
        if not job:
            return Response(status=204)
        log_app_event(
            "jobs",
            "worker.claim.success",
            job_id=job.id,
            organization_id=org_id,
            worker_id=worker_id,
        )
        return Response(JobSerializer(job).data)


class JobHeartbeatView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, job_id):
        org_id = _signed_org_id(request)
        if not org_id:
            log_app_event(
                "jobs",
                "worker.heartbeat.unauthorized",
                reason="missing_signed_org",
            )
            return Response(
                {"detail": "Signed organization context required"}, status=401
            )
        worker_id = request.data.get("worker_id")
        if not worker_id:
            log_app_event(
                "jobs",
                "worker.heartbeat.bad_request",
                reason="missing_worker_id",
            )
            return Response({"detail": "worker_id is required"}, status=400)
        job = get_object_or_404(Job, id=job_id, organization_id=org_id)
        try:
            heartbeat(job, worker_id)
        except ValueError as exc:
            log_app_event(
                "jobs",
                "worker.heartbeat.conflict",
                job_id=job.id,
                organization_id=org_id,
                worker_id=worker_id,
                error=str(exc),
            )
            return Response(
                {"detail": str(exc), "code": "lease_owner_mismatch"},
                status=409,
            )
        log_app_event(
            "jobs",
            "worker.heartbeat.success",
            job_id=job.id,
            organization_id=org_id,
            worker_id=worker_id,
        )
        return Response({"detail": "ok"})


class JobCompleteView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, job_id):
        org_id = _signed_org_id(request)
        if not org_id:
            log_app_event(
                "jobs",
                "worker.complete.unauthorized",
                reason="missing_signed_org",
            )
            return Response(
                {"detail": "Signed organization context required"}, status=401
            )
        worker_id = request.data.get("worker_id")
        if not worker_id:
            log_app_event(
                "jobs",
                "worker.complete.bad_request",
                reason="missing_worker_id",
            )
            return Response({"detail": "worker_id is required"}, status=400)
        job = get_object_or_404(Job, id=job_id, organization_id=org_id)
        try:
            require_lease_owner(job, worker_id)
        except ValueError as exc:
            log_app_event(
                "jobs",
                "worker.complete.conflict",
                job_id=job.id,
                organization_id=org_id,
                worker_id=worker_id,
                error=str(exc),
            )
            return Response(
                {"detail": str(exc), "code": "lease_owner_mismatch"},
                status=409,
            )
        mark_job_success(job)
        log_app_event(
            "jobs",
            "worker.complete.success",
            job_id=job.id,
            organization_id=org_id,
            worker_id=worker_id,
        )
        return Response({"detail": "job marked success"})


class JobFailView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, job_id):
        org_id = _signed_org_id(request)
        if not org_id:
            log_app_event(
                "jobs",
                "worker.fail.unauthorized",
                reason="missing_signed_org",
            )
            return Response(
                {"detail": "Signed organization context required"}, status=401
            )
        worker_id = request.data.get("worker_id")
        if not worker_id:
            log_app_event(
                "jobs",
                "worker.fail.bad_request",
                reason="missing_worker_id",
            )
            return Response({"detail": "worker_id is required"}, status=400)
        job = get_object_or_404(Job, id=job_id, organization_id=org_id)
        try:
            require_lease_owner(job, worker_id)
        except ValueError as exc:
            log_app_event(
                "jobs",
                "worker.fail.conflict",
                job_id=job.id,
                organization_id=org_id,
                worker_id=worker_id,
                error=str(exc),
            )
            return Response(
                {"detail": str(exc), "code": "lease_owner_mismatch"},
                status=409,
            )
        error_message = request.data.get("error_message", "worker reported failure")
        mark_job_failure(job, RuntimeError(error_message))
        log_app_event(
            "jobs",
            "worker.fail.success",
            job_id=job.id,
            organization_id=org_id,
            worker_id=worker_id,
        )
        return Response({"detail": "job marked failed"})


class JobFailuresView(APIView):
    def get(self, request, job_id):
        if not user_has_permission(request.user, "jobs.read"):
            return Response({"detail": "Missing permission: jobs.read"}, status=403)
        job = get_object_or_404(
            Job,
            id=job_id,
            **(
                {"organization": request.user.organization}
                if not is_platform_admin(request.user)
                else {}
            ),
        )
        return Response(
            JobFailureSerializer(job.failures.order_by("-created_at"), many=True).data
        )


class JobRowErrorListView(APIView):
    def get(self, request, job_id):
        if not user_has_permission(request.user, "jobs.read"):
            return Response({"detail": "Missing permission: jobs.read"}, status=403)
        job = get_object_or_404(
            Job,
            id=job_id,
            **(
                {"organization": request.user.organization}
                if not is_platform_admin(request.user)
                else {}
            ),
        )
        queryset = job.row_errors.order_by("resolved", "source_file", "row_number")
        return Response(IngestRowErrorSerializer(queryset, many=True).data)


class JobRowErrorResolveView(APIView):
    def post(self, request, error_id):
        if not user_has_permission(request.user, "jobs.write"):
            return Response({"detail": "Missing permission: jobs.write"}, status=403)

        row_error = get_object_or_404(
            IngestRowError,
            id=error_id,
            **(
                {"job__organization": request.user.organization}
                if not is_platform_admin(request.user)
                else {}
            ),
        )
        serializer = IngestRowErrorResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        row_error.resolved = True
        row_error.resolution_note = serializer.validated_data.get("resolution_note", "")
        row_error.resolved_by = request.user
        row_error.resolved_at = timezone.now()
        row_error.save(
            update_fields=["resolved", "resolution_note", "resolved_by", "resolved_at"]
        )
        return Response(IngestRowErrorSerializer(row_error).data)


class AttachmentDedupeCheckView(APIView):
    def post(self, request):
        if not user_has_permission(request.user, "jobs.write"):
            return Response({"detail": "Missing permission: jobs.write"}, status=403)

        source_signature = (request.data.get("source_signature") or "").strip()
        content_hash = (request.data.get("content_hash") or "").strip()
        first_seen_job_id = request.data.get("first_seen_job")

        if not source_signature or not content_hash:
            return Response(
                {"detail": "source_signature and content_hash are required"},
                status=400,
            )

        first_seen_job = None
        if first_seen_job_id:
            first_seen_job = get_object_or_404(
                Job,
                id=first_seen_job_id,
                **(
                    {"organization": request.user.organization}
                    if not is_platform_admin(request.user)
                    else {}
                ),
            )

        fingerprint, created = IngestAttachmentFingerprint.objects.get_or_create(
            organization=(
                first_seen_job.organization
                if first_seen_job
                else request.user.organization
            ),
            source_signature=source_signature,
            content_hash=content_hash,
            defaults={"first_seen_job": first_seen_job},
        )

        return Response(
            {
                "duplicate": not created,
                "fingerprint": IngestAttachmentFingerprintSerializer(fingerprint).data,
            }
        )
