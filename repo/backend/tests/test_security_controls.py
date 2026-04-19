import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from access.models import BaseRole, Role
from accounts.models import User, UserRole
from accounts.models import VerificationRequest
from core.crypto import encrypt_text
from core.structured_logging import JsonFormatter
from jobs.models import IngestRowError, Job, JobLease, JobStatus
from monitoring.models import AnomalyAlert, AlertSeverity
from trips.models import Trip, TripStatus
from organizations.models import Organization
from security.models import ApiClientKey


class BaseSecurityTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._previous_aes_key = os.environ.get("APP_AES256_KEY_B64")
        os.environ["APP_AES256_KEY_B64"] = (
            "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
        )

        suffix = cls.__name__.upper()
        cls.org = Organization.objects.create(
            name=f"Primary Org {suffix}", code=f"ORG_{suffix}_A"
        )
        cls.other_org = Organization.objects.create(
            name=f"Secondary Org {suffix}", code=f"ORG_{suffix}_B"
        )

        call_command("bootstrap_access")

        cls.org_admin = User.objects.create_user(
            username=f"orgadmin_{cls.__name__.lower()}",
            password="SecurePass1234",
            organization=cls.org,
            real_name="Org Admin",
            is_staff=True,
        )
        cls.other_admin = User.objects.create_user(
            username=f"otheradmin_{cls.__name__.lower()}",
            password="SecurePass1234",
            organization=cls.other_org,
            real_name="Other Admin",
            is_staff=True,
        )

        cls._assign_role(cls.org_admin, BaseRole.ORG_ADMIN)
        cls._assign_role(cls.other_admin, BaseRole.ORG_ADMIN)

    @classmethod
    def tearDownClass(cls):
        if cls._previous_aes_key is None:
            os.environ.pop("APP_AES256_KEY_B64", None)
        else:
            os.environ["APP_AES256_KEY_B64"] = cls._previous_aes_key
        super().tearDownClass()

    @classmethod
    def _assign_role(cls, user, role_code):
        role = Role.objects.get(organization=user.organization, code=role_code)
        UserRole.objects.get_or_create(user=user, role=role)

    @staticmethod
    def _create_api_key(organization, key_id, secret):
        return ApiClientKey.objects.create(
            organization=organization,
            key_id=key_id,
            secret_encrypted=encrypt_text(secret),
            secret_fingerprint=hashlib.sha256(secret.encode("utf-8")).hexdigest(),
            is_active=True,
        )

    def _signed_post(self, path, body, *, key_id, secret):
        ts = timezone.now().isoformat()
        nonce = str(uuid.uuid4())
        body_json = json.dumps(body, separators=(",", ":"))
        payload = "\n".join(["POST", path, ts, nonce, body_json])
        signature = hmac.new(
            secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        client = APIClient()
        return client.post(
            path,
            data=body_json,
            content_type="application/json",
            HTTP_X_KEY_ID=key_id,
            HTTP_X_SIGN_TIMESTAMP=ts,
            HTTP_X_SIGN_NONCE=nonce,
            HTTP_X_SIGNATURE=signature,
        )

    @staticmethod
    def _session_signature(*, method, path, timestamp, nonce, csrf_token):
        payload = "\n".join([method, path, timestamp, nonce])
        return hmac.new(
            csrf_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()


class WorkerClaimConcurrencyPolicyTests(BaseSecurityTestCase):
    def test_worker_claim_does_not_allow_client_limit_override(self):
        previous_limit = os.environ.get("OFFLINE_INGEST_CONCURRENCY_LIMIT")
        os.environ["OFFLINE_INGEST_CONCURRENCY_LIMIT"] = "3"
        try:
            for idx in range(3):
                running = Job.objects.create(
                    organization=self.org,
                    job_type="ingest.folder_scan",
                    source_path=f"/tmp/running-{idx}",
                    payload_json={},
                    trigger_type="manual",
                    status=JobStatus.RUNNING,
                    priority=1,
                    dedupe_key=f"running-{idx}",
                    started_at=timezone.now(),
                )
                JobLease.objects.create(
                    job=running,
                    worker_id=f"worker-{idx}",
                    lease_until=timezone.now() + timedelta(minutes=5),
                )

            pending = Job.objects.create(
                organization=self.org,
                job_type="ingest.folder_scan",
                source_path="/tmp/pending-limit",
                payload_json={},
                trigger_type="manual",
                status=JobStatus.PENDING,
                priority=1,
                dedupe_key="pending-limit",
            )

            secret = "claim-limit-secret-" * 4
            key = self._create_api_key(self.org, "claim-limit-key", secret)
            response = self._signed_post(
                "/api/jobs/worker/claim/",
                {
                    "worker_id": "worker-z",
                    "organization_id": self.org.id,
                    "concurrency_limit": 999,
                },
                key_id=key.key_id,
                secret=secret,
            )

            self.assertEqual(response.status_code, 204)
            pending.refresh_from_db()
            self.assertEqual(pending.status, JobStatus.PENDING)
        finally:
            if previous_limit is None:
                os.environ.pop("OFFLINE_INGEST_CONCURRENCY_LIMIT", None)
            else:
                os.environ["OFFLINE_INGEST_CONCURRENCY_LIMIT"] = previous_limit


class RequestSigningCoverageTests(BaseSecurityTestCase):
    def test_non_job_mutation_requires_signature_headers(self):
        response = APIClient().post(
            "/api/monitoring/thresholds/",
            {
                "metric": "job_failures",
                "operator": "gt",
                "threshold_value": 5,
                "severity": "high",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json().get("code"), "missing_signature_headers")

    def test_auth_login_stays_allowlisted_without_signature(self):
        response = APIClient().post(
            "/api/auth/login/",
            {
                "username": self.org_admin.username,
                "password": "WrongPass1234",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertNotEqual(payload.get("code"), "missing_signature_headers")

    def test_signed_non_job_mutation_passes_signing_gate(self):
        secret = "monitoring-signing-secret-" * 3
        key = self._create_api_key(self.org, "monitoring-sign-key", secret)

        response = self._signed_post(
            "/api/monitoring/thresholds/",
            {
                "metric": "job_failures",
                "operator": "gt",
                "threshold_value": 5,
                "severity": "high",
            },
            key_id=key.key_id,
            secret=secret,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json().get("detail"),
            "Authentication credentials were not provided.",
        )

    @override_settings(SESSION_REPLAY_REQUIRE_HEADERS=True)
    def test_authenticated_session_mutation_requires_replay_headers(self):
        client = APIClient()
        client.force_login(self.org_admin)

        response = client.post(
            "/api/auth/favorites/",
            {"kind": "trip", "reference_id": "session-missing-headers"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("code"), "missing_session_replay_headers")

    @override_settings(
        SESSION_REPLAY_REQUIRE_HEADERS=True,
        SESSION_SIGNING_REQUIRE_HEADERS=True,
    )
    def test_authenticated_session_mutation_requires_session_signature(self):
        client = APIClient()
        client.force_login(self.org_admin)

        timestamp = timezone.now().isoformat()
        nonce = "session-signature-required"
        response = client.post(
            "/api/auth/favorites/",
            {"kind": "trip", "reference_id": "session-signature-missing"},
            format="json",
            HTTP_X_REQUEST_TIMESTAMP=timestamp,
            HTTP_X_REQUEST_NONCE=nonce,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json().get("code"), "missing_session_signature_headers"
        )

    @override_settings(
        SESSION_REPLAY_REQUIRE_HEADERS=True,
        SESSION_SIGNING_REQUIRE_HEADERS=True,
    )
    def test_authenticated_session_mutation_invalid_session_signature_rejected(self):
        client = APIClient()
        client.force_login(self.org_admin)

        csrf_response = client.get("/api/auth/csrf/")
        csrf_token = csrf_response.json().get("csrfToken")

        timestamp = timezone.now().isoformat()
        nonce = "session-signature-invalid"
        bad_signature = "0" * 64
        if bad_signature == self._session_signature(
            method="POST",
            path="/api/auth/favorites/",
            timestamp=timestamp,
            nonce=nonce,
            csrf_token=csrf_token,
        ):
            bad_signature = "f" * 64

        response = client.post(
            "/api/auth/favorites/",
            {"kind": "trip", "reference_id": "session-signature-invalid"},
            format="json",
            HTTP_X_REQUEST_TIMESTAMP=timestamp,
            HTTP_X_REQUEST_NONCE=nonce,
            HTTP_X_SESSION_SIGNATURE=bad_signature,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json().get("code"), "invalid_session_signature")

    @override_settings(
        SESSION_REPLAY_REQUIRE_HEADERS=True,
        SESSION_SIGNING_REQUIRE_HEADERS=True,
    )
    def test_authenticated_session_mutation_replay_is_blocked(self):
        client = APIClient()
        client.force_login(self.org_admin)

        csrf_response = client.get("/api/auth/csrf/")
        csrf_token = csrf_response.json().get("csrfToken")

        timestamp = timezone.now().isoformat()
        nonce = "session-replay-nonce"
        payload = {"kind": "trip", "reference_id": "session-replay"}
        signature = self._session_signature(
            method="POST",
            path="/api/auth/favorites/",
            timestamp=timestamp,
            nonce=nonce,
            csrf_token=csrf_token,
        )

        first = client.post(
            "/api/auth/favorites/",
            payload,
            format="json",
            HTTP_X_REQUEST_TIMESTAMP=timestamp,
            HTTP_X_REQUEST_NONCE=nonce,
            HTTP_X_SESSION_SIGNATURE=signature,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(first.status_code, 201)

        second = client.post(
            "/api/auth/favorites/",
            payload,
            format="json",
            HTTP_X_REQUEST_TIMESTAMP=timestamp,
            HTTP_X_REQUEST_NONCE=nonce,
            HTTP_X_SESSION_SIGNATURE=signature,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json().get("code"), "replay_nonce_detected")


class JobDependencyValidationTests(BaseSecurityTestCase):
    def test_invalid_dependency_graph_returns_controlled_400(self):
        client = APIClient()
        client.force_login(self.org_admin)

        dependency = Job.objects.create(
            organization=self.org,
            job_type="ingest.folder_scan",
            source_path="/tmp/dep",
            payload_json={},
            trigger_type="manual",
            status=JobStatus.PENDING,
            priority=1,
            dedupe_key="dep-1",
        )

        with patch(
            "jobs.views.validate_dependency_graph",
            side_effect=ValueError("Dependency cycle detected"),
        ):
            response = client.post(
                "/api/jobs/",
                {
                    "job_type": "ingest.folder_scan",
                    "trigger_type": "manual",
                    "priority": 1,
                    "source_path": "/tmp/new-job",
                    "payload_json": {},
                    "dedupe_key": "new-job-with-invalid-deps",
                    "dependency_ids": [dependency.id],
                },
                format="json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("code"), "invalid_dependency_graph")
        self.assertIn("Dependency cycle detected", response.json().get("detail", ""))


class StructuredLoggingSanitizationTests(TestCase):
    def test_json_formatter_redacts_sensitive_event_fields(self):
        stream = StringIO()
        logger = logging.getLogger("harborops.sanitization-test")
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False

        logger.info(
            "security.event",
            extra={
                "event": {
                    "category": "security",
                    "action": "test",
                    "password": "should-not-appear",
                    "api_secret": "should-not-appear",
                    "nested": {"authorization_token": "hidden"},
                    "safe_field": "visible",
                }
            },
        )

        payload = json.loads(stream.getvalue().strip())
        event = payload["event"]
        self.assertEqual(event["password"], "[REDACTED]")
        self.assertEqual(event["api_secret"], "[REDACTED]")
        self.assertEqual(event["nested"]["authorization_token"], "[REDACTED]")
        self.assertEqual(event["safe_field"], "visible")


class ObjectAuthorizationEdgeTests(BaseSecurityTestCase):
    def setUp(self):
        self.org_admin_client = APIClient()
        self.org_admin_client.force_login(self.org_admin)
        self.other_admin_client = APIClient()
        self.other_admin_client.force_login(self.other_admin)

    def test_row_error_resolve_isolated_by_organization(self):
        other_job = Job.objects.create(
            organization=self.other_org,
            job_type="ingest.folder_scan",
            source_path="/tmp/other-org",
            payload_json={},
            trigger_type="manual",
            status=JobStatus.FAILED,
            priority=1,
            dedupe_key="other-org-row-error",
        )
        row_error = IngestRowError.objects.create(
            job=other_job,
            source_file="manifest.csv",
            row_number=1,
            error_message="Invalid row",
            raw_row_json={"trip_id": ""},
        )

        denied = self.org_admin_client.post(
            f"/api/jobs/row-errors/{row_error.id}/resolve/",
            {"resolution_note": "not mine"},
            format="json",
        )
        self.assertEqual(denied.status_code, 404)

        allowed = self.other_admin_client.post(
            f"/api/jobs/row-errors/{row_error.id}/resolve/",
            {"resolution_note": "fixed"},
            format="json",
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertTrue(allowed.json().get("resolved"))


class TripStateTransitionTests(BaseSecurityTestCase):
    def test_trip_publish_unpublish_state_transitions(self):
        client = APIClient()
        client.force_login(self.org_admin)

        create = client.post(
            "/api/trips/",
            {
                "title": "Transition Trip",
                "origin": "A",
                "destination": "B",
                "service_date": "2026-06-10",
                "pickup_window_start": "2026-06-10T10:00:00Z",
                "pickup_window_end": "2026-06-10T11:00:00Z",
                "timezone_id": "UTC",
                "signup_deadline": "2026-06-10T07:30:00Z",
                "capacity_limit": 4,
                "pricing_model": "flat",
                "fare_cents": 2500,
                "tax_bps": 0,
                "fee_cents": 0,
                "cancellation_cutoff_minutes": 60,
                "waypoints": [{"sequence": 1, "name": "Stop 1", "address": "Addr 1"}],
            },
            format="json",
        )
        self.assertEqual(create.status_code, 201)
        trip_id = create.json()["id"]

        publish = client.post(f"/api/trips/{trip_id}/publish/", {}, format="json")
        self.assertEqual(publish.status_code, 200)
        self.assertEqual(publish.json()["status"], TripStatus.LIVE)

        trip = Trip.objects.get(id=trip_id)
        self.assertEqual(trip.status, TripStatus.LIVE)
        self.assertIsNotNone(trip.published_at)

        unpublish = client.post(f"/api/trips/{trip_id}/unpublish/", {}, format="json")
        self.assertEqual(unpublish.status_code, 200)
        self.assertEqual(unpublish.json()["status"], TripStatus.UNPUBLISHED)

        trip.refresh_from_db()
        self.assertEqual(trip.status, TripStatus.UNPUBLISHED)


class JobsListBehaviorTests(BaseSecurityTestCase):
    def test_jobs_list_returns_empty_array_when_no_jobs(self):
        client = APIClient()
        client.force_login(self.org_admin)

        response = client.get("/api/jobs/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


class VerificationDuplicateReviewTests(BaseSecurityTestCase):
    def test_duplicate_reviewer_is_rejected_with_conflict(self):
        senior = User.objects.create_user(
            username=f"senior_{self.__class__.__name__.lower()}",
            password="SecurePass1234",
            organization=self.org,
            real_name="Senior User",
            is_staff=False,
        )
        self._assign_role(senior, BaseRole.SENIOR)

        verification = VerificationRequest.objects.create(
            user=senior,
            is_high_risk=False,
            attestation="I attest this is correct",
        )

        reviewer = APIClient()
        reviewer.force_login(self.org_admin)

        first = reviewer.post(
            f"/api/auth/verification-requests/{verification.id}/review/",
            {
                "verification_request": verification.id,
                "approved": True,
                "comments": "first review",
            },
            format="json",
        )
        self.assertEqual(first.status_code, 201)

        second = reviewer.post(
            f"/api/auth/verification-requests/{verification.id}/review/",
            {
                "verification_request": verification.id,
                "approved": True,
                "comments": "duplicate",
            },
            format="json",
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json().get("code"), "duplicate_reviewer")


class MonitoringCrossOrgAuthorizationTests(BaseSecurityTestCase):
    def test_cross_org_alert_acknowledge_is_denied(self):
        foreign_alert = AnomalyAlert.objects.create(
            organization=self.other_org,
            alert_type="failed_logins_spike",
            severity=AlertSeverity.WARNING,
            title="Foreign alert",
            details="Cross-tenant test",
            metadata_json={"source": "test"},
        )

        denied_client = APIClient()
        denied_client.force_login(self.org_admin)
        denied = denied_client.post(
            f"/api/monitoring/alerts/{foreign_alert.id}/ack/", {}, format="json"
        )
        self.assertEqual(denied.status_code, 404)

        foreign_alert.refresh_from_db()
        self.assertFalse(foreign_alert.acknowledged)

        allowed_client = APIClient()
        allowed_client.force_login(self.other_admin)
        allowed = allowed_client.post(
            f"/api/monitoring/alerts/{foreign_alert.id}/ack/", {}, format="json"
        )
        self.assertEqual(allowed.status_code, 200)

        foreign_alert.refresh_from_db()
        self.assertTrue(foreign_alert.acknowledged)
