import hashlib
import hmac
import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from access.models import BaseRole, Permission, Role, RolePermission
from accounts.models import (
    CaptchaChallenge,
    DataExportRequest,
    TravelerProfile,
    User,
    UserRole,
    VerificationRequest,
)
from audit.models import AuditEvent
from core.crypto import encrypt_text
from inventory.models import InventoryCountLine
from jobs.management.commands.run_offline_ingest_worker import (
    Command as OfflineIngestWorkerCommand,
)
from jobs.models import (
    IngestAttachmentFingerprint,
    Job,
    JobCheckpoint,
    JobDependency,
    JobLease,
    JobStatus,
)
from jobs.services import mark_job_success, run_folder_ingest_job
from monitoring.models import AnomalyAlert
from organizations.models import Organization
from security.models import ApiClientKey
from trips.models import Booking


class EndToEndSuite(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._previous_aes_key = os.environ.get("APP_AES256_KEY_B64")
        os.environ["APP_AES256_KEY_B64"] = (
            "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
        )

        cls.org = Organization.objects.create(
            name="Harbor Test Org", code="HARBOR_TEST"
        )
        cls.other_org = Organization.objects.create(
            name="Harbor Other Org", code="HARBOR_OTHER"
        )
        call_command("bootstrap_access")

        cls.org_admin = User.objects.create_user(
            username="orgadmin_test",
            password="SecurePass1234",
            organization=cls.org,
            real_name="Org Admin",
            is_staff=True,
        )
        cls.senior = User.objects.create_user(
            username="senior_test",
            password="SecurePass1234",
            organization=cls.org,
            real_name="Senior One",
        )
        cls.family = User.objects.create_user(
            username="family_test_user",
            password="SecurePass1234",
            organization=cls.org,
            real_name="Family User",
        )
        cls.caregiver = User.objects.create_user(
            username="caregiver_test_user",
            password="SecurePass1234",
            organization=cls.org,
            real_name="Caregiver User",
        )
        cls.other_admin = User.objects.create_user(
            username="other_admin",
            password="SecurePass1234",
            organization=cls.other_org,
            real_name="Other Org Admin",
            is_staff=True,
        )
        cls.platform_admin = User.objects.create_user(
            username="platform_admin_test",
            password="SecurePass1234",
            organization=cls.org,
            real_name="Platform Admin",
            is_staff=True,
        )

        cls._assign_role(cls.org_admin, BaseRole.ORG_ADMIN)
        cls._assign_role(cls.senior, BaseRole.SENIOR)
        cls._assign_role(cls.family, BaseRole.FAMILY_MEMBER)
        cls._assign_role(cls.caregiver, BaseRole.CAREGIVER)
        cls._assign_role(cls.other_admin, BaseRole.ORG_ADMIN)
        cls._assign_role(cls.platform_admin, BaseRole.PLATFORM_ADMIN)

        cls.admin_client = APIClient()
        cls.admin_client.force_login(cls.org_admin)

        cls.senior_client = APIClient()
        cls.senior_client.force_login(cls.senior)

        cls.family_client = APIClient()
        cls.family_client.force_login(cls.family)

        cls.caregiver_client = APIClient()
        cls.caregiver_client.force_login(cls.caregiver)

        cls.other_admin_client = APIClient()
        cls.other_admin_client.force_login(cls.other_admin)

        cls.platform_admin_client = APIClient()
        cls.platform_admin_client.force_login(cls.platform_admin)

    @classmethod
    def tearDownClass(cls):
        if cls._previous_aes_key is None:
            os.environ.pop("APP_AES256_KEY_B64", None)
        else:
            os.environ["APP_AES256_KEY_B64"] = cls._previous_aes_key
        super().tearDownClass()

    @classmethod
    def _assign_role(cls, user, role_code):
        role = Role.objects.get(organization=cls.org, code=role_code)
        UserRole.objects.get_or_create(user=user, role=role)

    def _signed_worker_post(
        self, path, body, secret, key_id, timestamp=None, nonce=None
    ):
        ts = timestamp or timezone.now().isoformat()
        nonce = nonce or str(uuid.uuid4())
        body_json = json.dumps(body, separators=(",", ":"))
        payload = "\n".join(["POST", path, ts, nonce, body_json])
        signature = hmac.new(
            secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return self.client.post(
            path,
            data=body_json,
            content_type="application/json",
            HTTP_X_KEY_ID=key_id,
            HTTP_X_SIGN_TIMESTAMP=ts,
            HTTP_X_SIGN_NONCE=nonce,
            HTTP_X_SIGNATURE=signature,
        )

    def test_01_registration_login_and_me_flow(self):
        client = APIClient()
        resp = client.post(
            "/api/auth/register/",
            {
                "organization_code": "HARBOR_TEST",
                "username": "family_test",
                "password": "FamilyPass1234",
                "real_name": "Family Member",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["username"], "family_test")

        login_resp = client.post(
            "/api/auth/login/",
            {"username": "family_test", "password": "FamilyPass1234"},
            format="json",
        )
        self.assertEqual(login_resp.status_code, 200)
        me_resp = client.get("/api/auth/me/")
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.data["username"], "family_test")

    def test_02_failed_login_captcha_and_lockout(self):
        client = APIClient()
        challenge_id = None
        captcha_answer = None
        for attempt in range(1, 11):
            payload = {"username": "senior_test", "password": "WrongPass1234"}
            if attempt >= 5:
                if challenge_id is None:
                    challenge_resp = client.post(
                        "/api/auth/captcha/challenge/",
                        {"username": "senior_test"},
                        format="json",
                    )
                    self.assertEqual(challenge_resp.status_code, 200)
                    challenge_id = challenge_resp.data["challenge_id"]
                    captcha_answer = str(
                        CaptchaChallenge.objects.get(challenge_id=challenge_id).answer
                    )
                payload["captcha_challenge_id"] = str(challenge_id)
                payload["captcha_response"] = str(captcha_answer or "")
            resp = client.post(
                "/api/auth/login/",
                payload,
                format="json",
            )
            self.assertEqual(resp.status_code, 400)
            if attempt >= 5:
                self.assertTrue(resp.data.get("requires_captcha", True))

        locked_resp = client.post(
            "/api/auth/login/",
            {"username": "senior_test", "password": "SecurePass1234"},
            format="json",
        )
        self.assertEqual(locked_resp.status_code, 423)
        self.assertIn("locked_until", locked_resp.data)

    def test_03_role_access_controls(self):
        trips_resp = self.senior_client.get("/api/trips/")
        self.assertEqual(trips_resp.status_code, 200)

        warehouse_resp = self.senior_client.get("/api/warehouses/")
        self.assertEqual(warehouse_resp.status_code, 403)

        jobs_resp = self.senior_client.get("/api/jobs/")
        self.assertEqual(jobs_resp.status_code, 403)

    def test_04_trip_versioning_and_reack_required(self):
        create_trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Clinic Shuttle",
                "origin": "North Center",
                "destination": "Clinic Annex",
                "service_date": "2026-03-25",
                "pickup_window_start": "2026-03-25T08:00:00Z",
                "pickup_window_end": "2026-03-25T09:00:00Z",
                "timezone_id": "America/Chicago",
                "signup_deadline": "2026-03-25T05:30:00Z",
                "capacity_limit": 3,
                "pricing_model": "per_seat",
                "fare_cents": 2500,
                "tax_bps": 0,
                "fee_cents": 100,
            },
            format="json",
        )
        self.assertEqual(create_trip.status_code, 201)
        trip_id = create_trip.data["id"]

        booking_resp = self.senior_client.post(
            f"/api/trips/{trip_id}/bookings/",
            {"care_priority": 1},
            format="json",
        )
        self.assertEqual(booking_resp.status_code, 201)

        update_resp = self.admin_client.patch(
            f"/api/trips/{trip_id}/",
            {"fare_cents": 2800, "change_summary": "Fare updated"},
            format="json",
        )
        self.assertEqual(update_resp.status_code, 200)
        self.assertEqual(update_resp.data["current_version"], 2)

        booking = Booking.objects.get(id=booking_resp.data["id"])
        self.assertTrue(booking.reack_required)

    def test_04b_trip_patch_replaces_waypoints_and_versions_snapshot(self):
        create_trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Waypoint Edit",
                "origin": "North Center",
                "destination": "Clinic Annex",
                "service_date": "2026-03-25",
                "pickup_window_start": "2026-03-25T08:00:00Z",
                "pickup_window_end": "2026-03-25T09:00:00Z",
                "timezone_id": "America/Chicago",
                "signup_deadline": "2026-03-25T05:30:00Z",
                "capacity_limit": 3,
                "pricing_model": "per_seat",
                "fare_cents": 2500,
                "tax_bps": 0,
                "fee_cents": 100,
                "waypoints": [
                    {"sequence": 1, "name": "Stop A", "address": "A Street"},
                    {"sequence": 2, "name": "Stop B", "address": "B Street"},
                ],
            },
            format="json",
        )
        self.assertEqual(create_trip.status_code, 201)
        trip_id = create_trip.data["id"]

        patch_resp = self.admin_client.patch(
            f"/api/trips/{trip_id}/",
            {
                "change_summary": "Adjusted pickup route",
                "waypoints": [
                    {"sequence": 1, "name": "Stop X", "address": "X Street"},
                    {"sequence": 2, "name": "Stop Y", "address": "Y Street"},
                ],
            },
            format="json",
        )
        self.assertEqual(patch_resp.status_code, 200)

        versions = self.admin_client.get(f"/api/trips/{trip_id}/versions/")
        self.assertEqual(versions.status_code, 200)
        self.assertEqual(
            versions.data[0]["snapshot_json"]["waypoints"][0]["name"], "Stop X"
        )
        self.assertEqual(
            versions.data[0]["snapshot_json"]["waypoints"][1]["name"], "Stop Y"
        )

    def test_04c_trip_patch_waypoint_reorder_add_remove_sets_reack(self):
        create_trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Waypoint Material Change",
                "origin": "North Center",
                "destination": "Clinic Annex",
                "service_date": "2026-03-25",
                "pickup_window_start": "2026-03-25T08:00:00Z",
                "pickup_window_end": "2026-03-25T09:00:00Z",
                "timezone_id": "America/Chicago",
                "signup_deadline": "2026-03-25T05:30:00Z",
                "capacity_limit": 3,
                "pricing_model": "per_seat",
                "fare_cents": 2500,
                "tax_bps": 0,
                "fee_cents": 100,
                "waypoints": [
                    {"sequence": 1, "name": "Stop A", "address": "A Street"},
                    {"sequence": 2, "name": "Stop B", "address": "B Street"},
                    {"sequence": 3, "name": "Stop C", "address": "C Street"},
                ],
            },
            format="json",
        )
        self.assertEqual(create_trip.status_code, 201)
        trip_id = create_trip.data["id"]

        booking_resp = self.senior_client.post(
            f"/api/trips/{trip_id}/bookings/",
            {"care_priority": 1},
            format="json",
        )
        self.assertEqual(booking_resp.status_code, 201)

        patch_resp = self.admin_client.patch(
            f"/api/trips/{trip_id}/",
            {
                "change_summary": "Route materially changed",
                "waypoints": [
                    {"sequence": 1, "name": "Stop C", "address": "C Street"},
                    {"sequence": 2, "name": "Stop A", "address": "A Street"},
                    {"sequence": 3, "name": "Stop D", "address": "D Street"},
                ],
            },
            format="json",
        )
        self.assertEqual(patch_resp.status_code, 200)
        self.assertEqual(patch_resp.data["current_version"], 2)
        self.assertEqual(
            [item["name"] for item in patch_resp.data["waypoints"]],
            ["Stop C", "Stop A", "Stop D"],
        )

        booking = Booking.objects.get(id=booking_resp.data["id"])
        self.assertTrue(booking.reack_required)

        versions = self.admin_client.get(f"/api/trips/{trip_id}/versions/")
        self.assertEqual(versions.status_code, 200)
        self.assertEqual(versions.data[0]["version_number"], 2)
        self.assertTrue(versions.data[0]["material_change"])
        self.assertEqual(
            [item["name"] for item in versions.data[0]["snapshot_json"]["waypoints"]],
            ["Stop C", "Stop A", "Stop D"],
        )

    def test_04d_trip_patch_waypoint_invalid_sequence_returns_400(self):
        create_trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Waypoint Validation",
                "origin": "North Center",
                "destination": "Clinic Annex",
                "service_date": "2026-03-25",
                "pickup_window_start": "2026-03-25T08:00:00Z",
                "pickup_window_end": "2026-03-25T09:00:00Z",
                "timezone_id": "America/Chicago",
                "signup_deadline": "2026-03-25T05:30:00Z",
                "capacity_limit": 3,
                "pricing_model": "per_seat",
                "fare_cents": 2500,
                "tax_bps": 0,
                "fee_cents": 100,
                "waypoints": [
                    {"sequence": 1, "name": "Stop A", "address": "A Street"},
                    {"sequence": 2, "name": "Stop B", "address": "B Street"},
                ],
            },
            format="json",
        )
        self.assertEqual(create_trip.status_code, 201)
        trip_id = create_trip.data["id"]

        invalid_patch = self.admin_client.patch(
            f"/api/trips/{trip_id}/",
            {
                "waypoints": [
                    {"sequence": 1, "name": "Stop X", "address": "X Street"},
                    {"sequence": 3, "name": "Stop Y", "address": "Y Street"},
                ]
            },
            format="json",
        )
        self.assertEqual(invalid_patch.status_code, 400)
        self.assertIn("waypoints", invalid_patch.data)

        trip_state = self.admin_client.get("/api/trips/")
        self.assertEqual(trip_state.status_code, 200)
        trip_payload = next(item for item in trip_state.data if item["id"] == trip_id)
        self.assertEqual(
            [item["name"] for item in trip_payload["waypoints"]], ["Stop A", "Stop B"]
        )
        self.assertEqual(trip_payload["current_version"], 1)

    def test_05_capacity_drop_waitlists_low_priority(self):
        trip_resp = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Capacity Test",
                "origin": "Origin",
                "destination": "Destination",
                "service_date": "2026-04-01",
                "pickup_window_start": "2026-04-01T10:00:00Z",
                "pickup_window_end": "2026-04-01T11:00:00Z",
                "timezone_id": "UTC",
                "signup_deadline": "2026-04-01T07:30:00Z",
                "capacity_limit": 3,
                "pricing_model": "flat",
                "fare_cents": 1000,
                "tax_bps": 0,
                "fee_cents": 0,
            },
            format="json",
        )
        trip_id = trip_resp.data["id"]

        rider2 = User.objects.create_user(
            username="rider2",
            password="SecurePass1234",
            organization=self.org,
            real_name="Rider Two",
        )
        rider3 = User.objects.create_user(
            username="rider3",
            password="SecurePass1234",
            organization=self.org,
            real_name="Rider Three",
        )
        self._assign_role(rider2, BaseRole.SENIOR)
        self._assign_role(rider3, BaseRole.SENIOR)

        client2 = APIClient()
        client2.force_login(rider2)
        client3 = APIClient()
        client3.force_login(rider3)

        self.senior_client.post(
            f"/api/trips/{trip_id}/bookings/", {"care_priority": 10}, format="json"
        )
        client2.post(
            f"/api/trips/{trip_id}/bookings/", {"care_priority": 5}, format="json"
        )
        client3.post(
            f"/api/trips/{trip_id}/bookings/", {"care_priority": 1}, format="json"
        )

        self.admin_client.patch(
            f"/api/trips/{trip_id}/",
            {"capacity_limit": 2, "change_summary": "Reduce capacity"},
            format="json",
        )

        statuses = list(
            Booking.objects.filter(trip_id=trip_id)
            .order_by("-care_priority")
            .values_list("status", flat=True)
        )
        self.assertEqual(statuses.count("confirmed"), 2)
        self.assertEqual(statuses.count("waitlisted"), 1)

    def test_06_warehouse_partner_effective_date_overlap_rejected(self):
        warehouse = self.admin_client.post(
            "/api/warehouses/", {"name": "W1", "region": "North"}, format="json"
        )
        self.assertEqual(warehouse.status_code, 201)

        zone = self.admin_client.post(
            "/api/warehouses/zones/",
            {
                "warehouse": warehouse.data["id"],
                "name": "Z1",
                "temperature_zone": "ambient",
                "hazmat_class": "none",
            },
            format="json",
        )
        self.assertEqual(zone.status_code, 201)

        location = self.admin_client.post(
            "/api/warehouses/locations/",
            {
                "zone": zone.data["id"],
                "code": "L1",
                "capacity_limit": "100.00",
                "capacity_unit": "units",
            },
            format="json",
        )
        self.assertEqual(location.status_code, 201)

        first = self.admin_client.post(
            "/api/warehouses/partners/",
            {
                "partner_type": "supplier",
                "external_code": "SUP-1",
                "display_name": "Supplier A",
                "effective_start": "2026-01-01",
                "effective_end": "2026-12-31",
                "data_json": {"tier": 1},
            },
            format="json",
        )
        self.assertEqual(first.status_code, 201)

        second = self.admin_client.post(
            "/api/warehouses/partners/",
            {
                "partner_type": "supplier",
                "external_code": "SUP-1",
                "display_name": "Supplier A Rev",
                "effective_start": "2026-06-01",
                "effective_end": "2027-01-01",
                "data_json": {"tier": 2},
            },
            format="json",
        )
        self.assertEqual(second.status_code, 400)

    def test_07_inventory_variance_closure_gate(self):
        warehouse = self.admin_client.post(
            "/api/warehouses/", {"name": "InvW", "region": "South"}, format="json"
        )
        zone = self.admin_client.post(
            "/api/warehouses/zones/",
            {
                "warehouse": warehouse.data["id"],
                "name": "InvZ",
                "temperature_zone": "ambient",
                "hazmat_class": "none",
            },
            format="json",
        )
        location = self.admin_client.post(
            "/api/warehouses/locations/",
            {
                "zone": zone.data["id"],
                "code": "INV-L1",
                "capacity_limit": "100.00",
                "capacity_unit": "units",
            },
            format="json",
        )

        plan = self.admin_client.post(
            "/api/inventory/plans/",
            {
                "title": "Plan1",
                "region": "South",
                "asset_type": "Wheelchairs",
                "mode": "full",
            },
            format="json",
        )
        task = self.admin_client.post(
            "/api/inventory/tasks/",
            {"plan": plan.data["id"], "location": location.data["id"]},
            format="json",
        )
        line_resp = self.admin_client.post(
            "/api/inventory/lines/",
            {
                "task": task.data["id"],
                "asset_code": "WC-1",
                "book_quantity": "100.00",
                "physical_quantity": "95.00",
            },
            format="json",
        )
        self.assertEqual(line_resp.status_code, 201)
        line_id = line_resp.data["id"]
        self.assertTrue(line_resp.data["requires_review"])

        blocked_close = self.admin_client.post(
            f"/api/inventory/lines/{line_id}/close/", {}, format="json"
        )
        self.assertEqual(blocked_close.status_code, 400)

        action = self.admin_client.post(
            f"/api/inventory/lines/{line_id}/corrective-action/",
            {
                "cause": "Counting error",
                "action": "Recount and relabel",
                "owner": self.org_admin.id,
                "due_date": "2026-04-01",
                "evidence": "photo",
            },
            format="json",
        )
        self.assertEqual(action.status_code, 201)

        self.admin_client.post(
            f"/api/inventory/lines/{line_id}/approve-action/",
            {"accountability_acknowledged": True},
            format="json",
        )
        close_resp = self.admin_client.post(
            f"/api/inventory/lines/{line_id}/close/",
            {"review_notes": "approved"},
            format="json",
        )
        self.assertEqual(close_resp.status_code, 200)
        line = InventoryCountLine.objects.get(id=line_id)
        self.assertTrue(line.closed)

    def test_08_jobs_dedupe_and_signed_worker_claim_with_replay_block(self):
        create_1 = self.admin_client.post(
            "/api/jobs/",
            {
                "job_type": "ingest_manifest",
                "trigger_type": "manual",
                "priority": 1,
                "source_path": "/data/incoming/manifest.csv",
                "payload_json": {"schema_version": "v1"},
                "dedupe_key": "manifest-v1",
            },
            format="json",
        )
        self.assertEqual(create_1.status_code, 201)

        create_2 = self.admin_client.post(
            "/api/jobs/",
            {
                "job_type": "ingest_manifest",
                "trigger_type": "manual",
                "priority": 1,
                "source_path": "/data/incoming/manifest.csv",
                "payload_json": {"schema_version": "v1"},
                "dedupe_key": "manifest-v1",
            },
            format="json",
        )
        self.assertEqual(create_2.status_code, 200)
        self.assertEqual(create_1.data["id"], create_2.data["id"])

        secret = "abcd" * 16
        ApiClientKey.objects.create(
            organization=self.org,
            key_id="worker-test",
            secret_encrypted=encrypt_text(secret),
            secret_fingerprint=hashlib.sha256(secret.encode("utf-8")).hexdigest(),
            is_active=True,
        )

        nonce = str(uuid.uuid4())
        claim_resp = self._signed_worker_post(
            "/api/jobs/worker/claim/",
            {"worker_id": "w1", "organization_id": self.org.id, "concurrency_limit": 3},
            secret=secret,
            key_id="worker-test",
            nonce=nonce,
        )
        self.assertEqual(claim_resp.status_code, 200)
        self.assertEqual(claim_resp.data["status"], "running")

        replay_resp = self._signed_worker_post(
            "/api/jobs/worker/claim/",
            {"worker_id": "w1", "organization_id": self.org.id, "concurrency_limit": 3},
            secret=secret,
            key_id="worker-test",
            nonce=nonce,
        )
        self.assertEqual(replay_resp.status_code, 401)

    def test_09_request_signing_expired_timestamp_rejected(self):
        secret = "efgh" * 16
        ApiClientKey.objects.create(
            organization=self.org,
            key_id="worker-expired",
            secret_encrypted=encrypt_text(secret),
            secret_fingerprint=hashlib.sha256(secret.encode("utf-8")).hexdigest(),
            is_active=True,
        )
        old_ts = (timezone.now() - timedelta(minutes=6)).isoformat()
        resp = self._signed_worker_post(
            "/api/jobs/worker/claim/",
            {"worker_id": "w2", "organization_id": self.org.id, "concurrency_limit": 3},
            secret=secret,
            key_id="worker-expired",
            timestamp=old_ts,
        )
        self.assertEqual(resp.status_code, 401)

    def test_10_sensitive_masking_and_unmask_session(self):
        create_profile = self.admin_client.post(
            "/api/auth/traveler-profiles/",
            {"display_name": "Senior Card", "identifier": "TRAVELER-123456789"},
            format="json",
        )
        self.assertEqual(create_profile.status_code, 201)
        self.assertTrue(create_profile.data["masked_identifier"].endswith("6789"))
        profile_id = create_profile.data["id"]

        blocked = self.admin_client.get(
            f"/api/security/traveler-profiles/{profile_id}/reveal/"
        )
        self.assertEqual(blocked.status_code, 403)

        session = self.admin_client.post(
            "/api/security/unmask-sessions/",
            {
                "field_name": f"traveler_identifier:{profile_id}",
                "reason": "verification",
                "minutes": 5,
            },
            format="json",
        )
        self.assertEqual(session.status_code, 201)

        reveal = self.admin_client.get(
            f"/api/security/traveler-profiles/{profile_id}/reveal/"
        )
        self.assertEqual(reveal.status_code, 200)
        self.assertEqual(reveal.data["identifier"], "TRAVELER-123456789")

    def test_11_high_risk_verification_needs_two_distinct_approvals(self):
        req_resp = self.senior_client.post(
            "/api/auth/verification-requests/",
            {
                "is_high_risk": True,
                "attestation": "I attest credentials are valid",
                "documents": [
                    {
                        "document_type": "government_id",
                        "file_name": "id-card.pdf",
                        "file_path": "/ingest/docs/id-card.pdf",
                        "mime_type": "application/pdf",
                        "file_size_bytes": 1024,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(req_resp.status_code, 201)
        req_id = req_resp.data["id"]

        review_1 = self.admin_client.post(
            f"/api/auth/verification-requests/{req_id}/review/",
            {"verification_request": req_id, "approved": True, "comments": "ok"},
            format="json",
        )
        self.assertEqual(review_1.status_code, 201)
        self.assertEqual(VerificationRequest.objects.get(id=req_id).status, "pending")

        review_2 = self.admin_client.post(
            f"/api/auth/verification-requests/{req_id}/review/",
            {"verification_request": req_id, "approved": True, "comments": "ok2"},
            format="json",
        )
        self.assertEqual(review_2.status_code, 409)
        self.assertEqual(VerificationRequest.objects.get(id=req_id).status, "pending")

        review_3 = self.platform_admin_client.post(
            f"/api/auth/verification-requests/{req_id}/review/",
            {
                "verification_request": req_id,
                "approved": True,
                "comments": "second reviewer",
            },
            format="json",
        )
        self.assertEqual(review_3.status_code, 201)

        self.senior.refresh_from_db()
        req = VerificationRequest.objects.get(id=req_id)
        self.assertEqual(req.status, "approved")
        self.assertTrue(self.senior.is_verified_identity)

    def test_12_unmasked_export_requires_permission(self):
        blocked = self.senior_client.post(
            "/api/auth/exports/request/",
            {
                "include_unmasked": True,
                "justification": "care handoff",
                "format": "json",
            },
            format="json",
        )
        self.assertEqual(blocked.status_code, 403)

        allowed = self.admin_client.post(
            "/api/auth/exports/request/",
            {
                "include_unmasked": True,
                "justification": "audit review",
                "format": "json",
            },
            format="json",
        )
        self.assertEqual(allowed.status_code, 201)

    def test_12b_export_request_lifecycle_ready_and_download_access(self):
        created = self.senior_client.post(
            "/api/auth/exports/request/",
            {
                "include_unmasked": False,
                "justification": "",
                "format": "json",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["status"], "pending")

        call_command("process_exports", "--limit", "10")

        req = DataExportRequest.objects.get(id=created.data["id"])
        self.assertEqual(req.status, DataExportRequest.Status.READY)
        self.assertTrue(req.file_path)
        self.assertGreater(req.file_size_bytes, 0)
        self.assertTrue(req.checksum_sha256)

        owner_download = self.senior_client.get(f"/api/auth/exports/{req.id}/download/")
        self.assertEqual(owner_download.status_code, 200)

        denied_same_org = self.family_client.get(
            f"/api/auth/exports/{req.id}/download/"
        )
        self.assertEqual(denied_same_org.status_code, 403)

        admin_same_org = self.admin_client.get(f"/api/auth/exports/{req.id}/download/")
        self.assertEqual(admin_same_org.status_code, 200)

        request_audit_exists = AuditEvent.objects.filter(
            event_type="export.requested", resource_id=str(req.id)
        ).exists()
        download_audit_exists = AuditEvent.objects.filter(
            event_type="export.downloaded", resource_id=str(req.id)
        ).exists()
        self.assertTrue(request_audit_exists)
        self.assertTrue(download_audit_exists)

    def test_12c_export_processor_handles_failure_state(self):
        created = self.admin_client.post(
            "/api/auth/exports/request/",
            {
                "include_unmasked": True,
                "justification": "auditable handoff",
                "format": "xml",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)

        call_command("process_exports", "--limit", "10")
        req = DataExportRequest.objects.get(id=created.data["id"])
        self.assertEqual(req.status, DataExportRequest.Status.FAILED)
        self.assertIn("Unsupported export format", req.failure_reason)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type="export.failed", resource_id=str(req.id)
            ).exists()
        )

    def test_13_idempotency_key_replay(self):
        key = str(uuid.uuid4())
        first = self.admin_client.post(
            "/api/warehouses/",
            {"name": "Idempotent-W", "region": "East"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        second = self.admin_client.post(
            "/api/warehouses/",
            {"name": "Idempotent-W", "region": "East"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        replay_payload = json.loads(second.content.decode("utf-8"))
        self.assertEqual(first.data["id"], replay_payload["id"])

    def test_14_anomaly_detection_and_monitoring_access(self):
        for _ in range(12):
            AuditEvent.objects.create(
                organization=self.org,
                actor=self.org_admin,
                event_type="auth.login.failed",
                resource_type="user",
                resource_id=str(self.senior.id),
                metadata_json={},
            )

        call_command("detect_anomalies")
        self.assertTrue(AnomalyAlert.objects.filter(organization=self.org).exists())

        admin_alerts = self.admin_client.get("/api/monitoring/alerts/")
        self.assertEqual(admin_alerts.status_code, 200)

        senior_alerts = self.senior_client.get("/api/monitoring/alerts/")
        self.assertEqual(senior_alerts.status_code, 403)

    def test_14b_monitoring_threshold_write_requires_monitoring_write(self):
        monitoring_user = User.objects.create_user(
            username="monitoring_reader",
            password="SecurePass1234",
            organization=self.org,
            real_name="Monitoring Reader",
        )
        monitoring_role = Role.objects.create(
            organization=self.org,
            code="monitoring_viewer",
            name="Monitoring Viewer",
            is_base_role=False,
        )
        RolePermission.objects.create(
            role=monitoring_role,
            permission=Permission.objects.get(code="monitoring.read"),
        )
        UserRole.objects.create(user=monitoring_user, role=monitoring_role)

        monitoring_client = APIClient()
        monitoring_client.login(username="monitoring_reader", password="SecurePass1234")

        read_resp = monitoring_client.get("/api/monitoring/thresholds/")
        self.assertEqual(read_resp.status_code, 200)

        denied_create = monitoring_client.post(
            "/api/monitoring/thresholds/",
            {
                "alert_type": "job.failure_rate",
                "numeric_threshold": 10,
                "window_minutes": 60,
            },
            format="json",
        )
        self.assertEqual(denied_create.status_code, 403)
        self.assertEqual(
            denied_create.data["detail"], "Missing permission: monitoring.write"
        )

        allowed_create = self.admin_client.post(
            "/api/monitoring/thresholds/",
            {
                "alert_type": "job.failure_rate",
                "numeric_threshold": 10,
                "window_minutes": 60,
            },
            format="json",
        )
        self.assertEqual(allowed_create.status_code, 201)

    def test_15_trip_fare_estimate_endpoint(self):
        trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Fare Test",
                "origin": "A",
                "destination": "B",
                "service_date": "2026-04-02",
                "pickup_window_start": "2026-04-02T10:00:00Z",
                "pickup_window_end": "2026-04-02T11:00:00Z",
                "timezone_id": "UTC",
                "signup_deadline": "2026-04-02T07:30:00Z",
                "capacity_limit": 10,
                "pricing_model": "per_seat",
                "fare_cents": 2000,
                "tax_bps": 750,
                "fee_cents": 150,
            },
            format="json",
        )
        self.assertEqual(trip.status_code, 201)

        estimate = self.admin_client.get(
            f"/api/trips/{trip.data['id']}/fare-estimate/?seats=2"
        )
        self.assertEqual(estimate.status_code, 200)
        self.assertEqual(estimate.data["total_cents"], 4461)

    def test_16_booking_cancellation_cutoff_enforced(self):
        pickup_start = (timezone.now() + timedelta(days=2)).replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        pickup_end = pickup_start + timedelta(hours=1)
        signup_deadline = pickup_start - timedelta(hours=3)
        trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Cancel Cutoff",
                "origin": "A",
                "destination": "B",
                "service_date": pickup_start.date().isoformat(),
                "pickup_window_start": pickup_start.isoformat().replace("+00:00", "Z"),
                "pickup_window_end": pickup_end.isoformat().replace("+00:00", "Z"),
                "timezone_id": "UTC",
                "signup_deadline": signup_deadline.isoformat().replace("+00:00", "Z"),
                "capacity_limit": 2,
                "pricing_model": "flat",
                "fare_cents": 1000,
                "tax_bps": 0,
                "fee_cents": 0,
                "cancellation_cutoff_minutes": 100000,
            },
            format="json",
        )
        booking = self.senior_client.post(
            f"/api/trips/{trip.data['id']}/bookings/",
            {"care_priority": 1},
            format="json",
        )
        self.assertEqual(booking.status_code, 201)

        cutoff_resp = self.senior_client.post(
            f"/api/trips/bookings/{booking.data['id']}/cancel/",
            {"reason": "Cannot attend"},
            format="json",
        )
        self.assertEqual(cutoff_resp.status_code, 400)

    def test_16b_cancel_and_refund_require_booking_write_permission(self):
        pickup_start = (timezone.now() + timedelta(days=2)).replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        pickup_end = pickup_start + timedelta(hours=1)
        signup_deadline = pickup_start - timedelta(hours=3)
        trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Booking Permission Gate",
                "origin": "A",
                "destination": "B",
                "service_date": pickup_start.date().isoformat(),
                "pickup_window_start": pickup_start.isoformat().replace("+00:00", "Z"),
                "pickup_window_end": pickup_end.isoformat().replace("+00:00", "Z"),
                "timezone_id": "UTC",
                "signup_deadline": signup_deadline.isoformat().replace("+00:00", "Z"),
                "capacity_limit": 2,
                "pricing_model": "flat",
                "fare_cents": 1000,
                "tax_bps": 0,
                "fee_cents": 0,
                "cancellation_cutoff_minutes": 0,
            },
            format="json",
        )
        booking = self.senior_client.post(
            f"/api/trips/{trip.data['id']}/bookings/",
            {"care_priority": 1},
            format="json",
        )
        self.assertEqual(booking.status_code, 201)

        restricted_user = User.objects.create_user(
            username="booking_reader_only",
            password="SecurePass1234",
            organization=self.org,
            real_name="Booking Reader",
        )
        restricted_role = Role.objects.create(
            organization=self.org,
            code="booking_reader_role",
            name="Booking Reader Role",
            is_base_role=False,
        )
        RolePermission.objects.create(
            role=restricted_role,
            permission=Permission.objects.get(code="trip.read"),
        )
        UserRole.objects.create(user=restricted_user, role=restricted_role)
        restricted_client = APIClient()
        restricted_client.force_login(restricted_user)

        cancel_denied = restricted_client.post(
            f"/api/trips/bookings/{booking.data['id']}/cancel/",
            {"reason": "no permission"},
            format="json",
        )
        self.assertEqual(cancel_denied.status_code, 403)

        refund_denied = restricted_client.post(
            f"/api/trips/bookings/{booking.data['id']}/refund-request/",
            {"reason": "no permission"},
            format="json",
        )
        self.assertEqual(refund_denied.status_code, 403)

        cancel_allowed = self.senior_client.post(
            f"/api/trips/bookings/{booking.data['id']}/cancel/",
            {"reason": "change of plans"},
            format="json",
        )
        self.assertEqual(cancel_allowed.status_code, 200, cancel_allowed.data)

        refund_allowed = self.senior_client.post(
            f"/api/trips/bookings/{booking.data['id']}/refund-request/",
            {"reason": "Need refund"},
            format="json",
        )
        self.assertEqual(refund_allowed.status_code, 201)

    def test_17_refund_flow_end_to_end(self):
        pickup_start = (timezone.now() + timedelta(days=2)).replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        pickup_end = pickup_start + timedelta(hours=1)
        signup_deadline = pickup_start - timedelta(hours=3)

        trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Refund Flow",
                "origin": "A",
                "destination": "B",
                "service_date": pickup_start.date().isoformat(),
                "pickup_window_start": pickup_start.isoformat().replace("+00:00", "Z"),
                "pickup_window_end": pickup_end.isoformat().replace("+00:00", "Z"),
                "timezone_id": "UTC",
                "signup_deadline": signup_deadline.isoformat().replace("+00:00", "Z"),
                "capacity_limit": 2,
                "pricing_model": "flat",
                "fare_cents": 1200,
                "tax_bps": 500,
                "fee_cents": 100,
                "cancellation_cutoff_minutes": 0,
            },
            format="json",
        )
        booking = self.senior_client.post(
            f"/api/trips/{trip.data['id']}/bookings/",
            {"care_priority": 1},
            format="json",
        )
        self.assertEqual(booking.status_code, 201)

        cancel = self.senior_client.post(
            f"/api/trips/bookings/{booking.data['id']}/cancel/",
            {"reason": "Medical"},
            format="json",
        )
        self.assertEqual(cancel.status_code, 200)
        self.assertEqual(cancel.data["status"], "cancelled")

        refund_request = self.senior_client.post(
            f"/api/trips/bookings/{booking.data['id']}/refund-request/",
            {"reason": "Need refund"},
            format="json",
        )
        self.assertEqual(refund_request.status_code, 201)
        self.assertEqual(refund_request.data["status"], "pending")

        refund_decision = self.admin_client.post(
            f"/api/trips/bookings/{booking.data['id']}/refund-decision/",
            {"decision": "approved"},
            format="json",
        )
        self.assertEqual(refund_decision.status_code, 200)
        self.assertEqual(refund_decision.data["status"], "approved")

    def test_18_no_show_and_timeline(self):
        trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "No Show Flow",
                "origin": "A",
                "destination": "B",
                "service_date": "2026-04-05",
                "pickup_window_start": "2020-04-05T10:00:00Z",
                "pickup_window_end": "2020-04-05T11:00:00Z",
                "timezone_id": "UTC",
                "signup_deadline": "2020-04-05T07:30:00Z",
                "capacity_limit": 2,
                "pricing_model": "flat",
                "fare_cents": 900,
                "tax_bps": 0,
                "fee_cents": 0,
            },
            format="json",
        )
        booking = self.senior_client.post(
            f"/api/trips/{trip.data['id']}/bookings/",
            {"care_priority": 1},
            format="json",
        )
        self.assertEqual(booking.status_code, 201)

        no_show = self.admin_client.post(
            f"/api/trips/bookings/{booking.data['id']}/no-show/",
            {"reason": "Missed pickup"},
            format="json",
        )
        self.assertEqual(no_show.status_code, 200)
        self.assertEqual(no_show.data["status"], "no_show")

        timeline = self.admin_client.get(
            f"/api/trips/bookings/{booking.data['id']}/timeline/"
        )
        self.assertEqual(timeline.status_code, 200)
        self.assertGreaterEqual(len(timeline.data), 2)

    def test_19_trip_booking_list_for_operations(self):
        trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Trip Booking List",
                "origin": "A",
                "destination": "B",
                "service_date": "2026-04-06",
                "pickup_window_start": "2026-04-06T10:00:00Z",
                "pickup_window_end": "2026-04-06T11:00:00Z",
                "timezone_id": "UTC",
                "signup_deadline": "2026-04-06T07:30:00Z",
                "capacity_limit": 2,
                "pricing_model": "flat",
                "fare_cents": 1000,
                "tax_bps": 0,
                "fee_cents": 0,
            },
            format="json",
        )
        self.assertEqual(trip.status_code, 201)

        booking = self.senior_client.post(
            f"/api/trips/{trip.data['id']}/bookings/",
            {"care_priority": 2},
            format="json",
        )
        self.assertEqual(booking.status_code, 201)

        list_resp = self.admin_client.get(f"/api/trips/{trip.data['id']}/bookings/")
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(len(list_resp.data), 1)
        self.assertEqual(list_resp.data[0]["id"], booking.data["id"])

    def test_20_verification_reviewer_can_list_org_requests(self):
        req_resp = self.senior_client.post(
            "/api/auth/verification-requests/",
            {
                "is_high_risk": False,
                "attestation": "Need access",
                "documents": [
                    {
                        "document_type": "credential",
                        "file_name": "cred.pdf",
                        "file_path": "secure/cred.pdf",
                        "mime_type": "application/pdf",
                        "file_size_bytes": 2048,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(req_resp.status_code, 201)

        reviewer_list = self.admin_client.get("/api/auth/verification-requests/")
        self.assertEqual(reviewer_list.status_code, 200)
        self.assertTrue(
            any(item["id"] == req_resp.data["id"] for item in reviewer_list.data)
        )

    def test_21_worker_endpoints_enforce_signed_org_context(self):
        create_job = self.admin_client.post(
            "/api/jobs/",
            {
                "job_type": "ingest_manifest",
                "trigger_type": "manual",
                "priority": 1,
                "source_path": "/data/incoming/tenant-a.csv",
                "payload_json": {"schema_version": "v1"},
                "dedupe_key": "tenant-a-worker",
            },
            format="json",
        )
        self.assertEqual(create_job.status_code, 201)
        job_id = create_job.data["id"]

        secret_a = "alpha" * 16
        secret_b = "bravo" * 16
        ApiClientKey.objects.create(
            organization=self.org,
            key_id="worker-org-a",
            secret_encrypted=encrypt_text(secret_a),
            secret_fingerprint=hashlib.sha256(secret_a.encode("utf-8")).hexdigest(),
            is_active=True,
        )
        ApiClientKey.objects.create(
            organization=self.other_org,
            key_id="worker-org-b",
            secret_encrypted=encrypt_text(secret_b),
            secret_fingerprint=hashlib.sha256(secret_b.encode("utf-8")).hexdigest(),
            is_active=True,
        )

        mismatch_claim = self._signed_worker_post(
            "/api/jobs/worker/claim/",
            {
                "worker_id": "worker-a",
                "organization_id": self.other_org.id,
                "concurrency_limit": 2,
            },
            secret=secret_a,
            key_id="worker-org-a",
        )
        self.assertEqual(mismatch_claim.status_code, 403)
        self.assertEqual(Job.objects.get(id=job_id).status, "pending")

        claim = self._signed_worker_post(
            "/api/jobs/worker/claim/",
            {"worker_id": "worker-a", "concurrency_limit": 2},
            secret=secret_a,
            key_id="worker-org-a",
        )
        self.assertEqual(claim.status_code, 200)
        self.assertEqual(claim.data["id"], job_id)

        cross_heartbeat = self._signed_worker_post(
            f"/api/jobs/worker/{job_id}/heartbeat/",
            {"worker_id": "worker-b"},
            secret=secret_b,
            key_id="worker-org-b",
        )
        self.assertEqual(cross_heartbeat.status_code, 404)

        cross_complete = self._signed_worker_post(
            f"/api/jobs/worker/{job_id}/complete/",
            {"worker_id": "worker-b"},
            secret=secret_b,
            key_id="worker-org-b",
        )
        self.assertEqual(cross_complete.status_code, 404)

        cross_fail = self._signed_worker_post(
            f"/api/jobs/worker/{job_id}/fail/",
            {"worker_id": "worker-b", "error_message": "should not apply"},
            secret=secret_b,
            key_id="worker-org-b",
        )
        self.assertEqual(cross_fail.status_code, 404)
        self.assertEqual(Job.objects.get(id=job_id).status, "running")

        heartbeat_ok = self._signed_worker_post(
            f"/api/jobs/worker/{job_id}/heartbeat/",
            {"worker_id": "worker-a"},
            secret=secret_a,
            key_id="worker-org-a",
        )
        self.assertEqual(heartbeat_ok.status_code, 200)

        complete_ok = self._signed_worker_post(
            f"/api/jobs/worker/{job_id}/complete/",
            {"worker_id": "worker-a"},
            secret=secret_a,
            key_id="worker-org-a",
        )
        self.assertEqual(complete_ok.status_code, 200)

        self.assertEqual(Job.objects.get(id=job_id).status, "success")

    def test_22_booking_visibility_role_matrix(self):
        trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Visibility Matrix",
                "origin": "A",
                "destination": "B",
                "service_date": "2026-04-07",
                "pickup_window_start": "2026-04-07T10:00:00Z",
                "pickup_window_end": "2026-04-07T11:00:00Z",
                "timezone_id": "UTC",
                "signup_deadline": "2026-04-07T07:30:00Z",
                "capacity_limit": 5,
                "pricing_model": "flat",
                "fare_cents": 1000,
                "tax_bps": 0,
                "fee_cents": 0,
            },
            format="json",
        )
        self.assertEqual(trip.status_code, 201)

        senior_booking = self.senior_client.post(
            f"/api/trips/{trip.data['id']}/bookings/",
            {"care_priority": 2},
            format="json",
        )
        family_booking = self.family_client.post(
            f"/api/trips/{trip.data['id']}/bookings/",
            {"care_priority": 1},
            format="json",
        )
        self.assertEqual(senior_booking.status_code, 201)
        self.assertEqual(family_booking.status_code, 201)

        admin_list = self.admin_client.get(f"/api/trips/{trip.data['id']}/bookings/")
        caregiver_list = self.caregiver_client.get(
            f"/api/trips/{trip.data['id']}/bookings/"
        )
        senior_list = self.senior_client.get(f"/api/trips/{trip.data['id']}/bookings/")
        family_list = self.family_client.get(f"/api/trips/{trip.data['id']}/bookings/")

        self.assertEqual(admin_list.status_code, 200)
        self.assertEqual(caregiver_list.status_code, 200)
        self.assertEqual(senior_list.status_code, 200)
        self.assertEqual(family_list.status_code, 200)

        self.assertEqual(len(admin_list.data), 2)
        self.assertEqual(len(caregiver_list.data), 2)
        self.assertEqual(len(senior_list.data), 1)
        self.assertEqual(len(family_list.data), 1)

        self.assertEqual(senior_list.data[0]["rider"], self.senior.id)
        self.assertEqual(family_list.data[0]["rider"], self.family.id)

    def test_23_inventory_variance_classification_includes_data_mismatch(self):
        warehouse = self.admin_client.post(
            "/api/warehouses/", {"name": "Mismatch-W", "region": "South"}, format="json"
        )
        zone = self.admin_client.post(
            "/api/warehouses/zones/",
            {
                "warehouse": warehouse.data["id"],
                "name": "Mismatch-Z",
                "temperature_zone": "ambient",
                "hazmat_class": "none",
            },
            format="json",
        )
        location = self.admin_client.post(
            "/api/warehouses/locations/",
            {
                "zone": zone.data["id"],
                "code": "MISMATCH-L1",
                "capacity_limit": "100.00",
                "capacity_unit": "units",
            },
            format="json",
        )
        plan = self.admin_client.post(
            "/api/inventory/plans/",
            {
                "title": "Mismatch Plan",
                "region": "South",
                "asset_type": "Medical",
                "mode": "full",
            },
            format="json",
        )
        task = self.admin_client.post(
            "/api/inventory/tasks/",
            {"plan": plan.data["id"], "location": location.data["id"]},
            format="json",
        )

        missing = self.admin_client.post(
            "/api/inventory/lines/",
            {
                "task": task.data["id"],
                "asset_code": "MED-1",
                "book_quantity": "10.00",
                "physical_quantity": "5.00",
            },
            format="json",
        )
        extra = self.admin_client.post(
            "/api/inventory/lines/",
            {
                "task": task.data["id"],
                "asset_code": "MED-2",
                "book_quantity": "5.00",
                "physical_quantity": "9.00",
            },
            format="json",
        )
        mismatch = self.admin_client.post(
            "/api/inventory/lines/",
            {
                "task": task.data["id"],
                "asset_code": "MED-3",
                "book_quantity": "8.00",
                "physical_quantity": "8.00",
                "observed_asset_code": "MED-3-ALT",
                "attribute_mismatch": True,
            },
            format="json",
        )

        self.assertEqual(missing.status_code, 201)
        self.assertEqual(extra.status_code, 201)
        self.assertEqual(mismatch.status_code, 201)
        self.assertEqual(missing.data["variance_type"], "missing")
        self.assertEqual(extra.data["variance_type"], "extra")
        self.assertEqual(mismatch.data["variance_type"], "data_mismatch")
        self.assertTrue(mismatch.data["requires_review"])

    def test_24_favorites_comparisons_and_local_reminders_lifecycle(self):
        favorite = self.senior_client.post(
            "/api/auth/favorites/",
            {"kind": "trip", "reference_id": "trip-100"},
            format="json",
        )
        self.assertEqual(favorite.status_code, 201)

        comparison = self.senior_client.post(
            "/api/auth/comparisons/",
            {"kind": "plan", "reference_id": "plan-11"},
            format="json",
        )
        self.assertEqual(comparison.status_code, 201)

        reminder = self.senior_client.post(
            "/api/auth/alerts/",
            {"title": "Care reminder", "message": "Bring medication card"},
            format="json",
        )
        self.assertEqual(reminder.status_code, 201)
        self.assertFalse(reminder.data["acknowledged"])

        own_favorites = self.senior_client.get("/api/auth/favorites/")
        own_comparisons = self.senior_client.get("/api/auth/comparisons/")
        own_alerts = self.senior_client.get("/api/auth/alerts/")
        self.assertEqual(len(own_favorites.data), 1)
        self.assertEqual(len(own_comparisons.data), 1)
        self.assertEqual(len(own_alerts.data), 1)

        family_favorites = self.family_client.get("/api/auth/favorites/")
        family_comparisons = self.family_client.get("/api/auth/comparisons/")
        family_alerts = self.family_client.get("/api/auth/alerts/")
        self.assertEqual(len(family_favorites.data), 0)
        self.assertEqual(len(family_comparisons.data), 0)
        self.assertEqual(len(family_alerts.data), 0)

        ack = self.senior_client.post(
            f"/api/auth/alerts/{reminder.data['id']}/acknowledge/", {}, format="json"
        )
        self.assertEqual(ack.status_code, 200)
        self.assertTrue(ack.data["acknowledged"])

        del_favorite = self.senior_client.delete(
            f"/api/auth/favorites/{favorite.data['id']}/"
        )
        del_comparison = self.senior_client.delete(
            f"/api/auth/comparisons/{comparison.data['id']}/"
        )
        self.assertEqual(del_favorite.status_code, 204)
        self.assertEqual(del_comparison.status_code, 204)

        family_delete_attempt = self.family_client.delete(
            f"/api/auth/favorites/{favorite.data['id']}/"
        )
        self.assertEqual(family_delete_attempt.status_code, 404)

    def test_25_signed_worker_invalid_signature_rejected(self):
        ApiClientKey.objects.create(
            organization=self.org,
            key_id="worker-invalid-sig",
            secret_encrypted=encrypt_text("valid-secret"),
            secret_fingerprint=hashlib.sha256(
                "valid-secret".encode("utf-8")
            ).hexdigest(),
            is_active=True,
        )

        invalid = self._signed_worker_post(
            "/api/jobs/worker/claim/",
            {"worker_id": "w-invalid", "concurrency_limit": 1},
            secret="wrong-secret",
            key_id="worker-invalid-sig",
        )
        self.assertEqual(invalid.status_code, 401)

    def test_25b_request_signing_scope_covers_jobs_mutations(self):
        payload = {
            "job_type": "ingest_manifest",
            "trigger_type": "manual",
            "priority": 1,
            "source_path": "/data/incoming/signed-scope.csv",
            "payload_json": {},
            "dedupe_key": "signed-scope",
        }
        unsigned_create = self.client.post(
            "/api/jobs/",
            payload,
            format="json",
        )
        self.assertEqual(unsigned_create.status_code, 401)
        unsigned_payload = json.loads(unsigned_create.content.decode("utf-8"))
        self.assertEqual(unsigned_payload["detail"], "Missing signature headers")
        self.assertEqual(unsigned_payload["code"], "missing_signature_headers")

        secret = "jobs-scope" * 8
        ApiClientKey.objects.create(
            organization=self.org,
            key_id="worker-jobs-scope",
            secret_encrypted=encrypt_text(secret),
            secret_fingerprint=hashlib.sha256(secret.encode("utf-8")).hexdigest(),
            is_active=True,
        )

        expired = self._signed_worker_post(
            "/api/jobs/",
            {**payload, "dedupe_key": "signed-scope-expired"},
            secret=secret,
            key_id="worker-jobs-scope",
            timestamp=(timezone.now() - timedelta(minutes=6)).isoformat(),
        )
        self.assertEqual(expired.status_code, 401)
        expired_payload = json.loads(expired.content.decode("utf-8"))
        self.assertEqual(expired_payload["code"], "signature_timestamp_expired")

        nonce = str(uuid.uuid4())
        replay_first = self._signed_worker_post(
            "/api/jobs/",
            {**payload, "dedupe_key": "signed-scope-replay"},
            secret=secret,
            key_id="worker-jobs-scope",
            nonce=nonce,
        )
        self.assertEqual(replay_first.status_code, 201)

        replay_second = self._signed_worker_post(
            "/api/jobs/",
            {**payload, "dedupe_key": "signed-scope-replay-2"},
            secret=secret,
            key_id="worker-jobs-scope",
            nonce=nonce,
        )
        self.assertEqual(replay_second.status_code, 401)
        replay_payload = json.loads(replay_second.content.decode("utf-8"))
        self.assertEqual(replay_payload["code"], "replay_nonce_detected")

        signed_create = self._signed_worker_post(
            "/api/jobs/",
            {**payload, "dedupe_key": "signed-scope-success"},
            secret=secret,
            key_id="worker-jobs-scope",
        )
        self.assertEqual(signed_create.status_code, 201)

        unsigned_retry = self.client.post(
            f"/api/jobs/{signed_create.data['id']}/retry/",
            {},
            format="json",
        )
        self.assertEqual(unsigned_retry.status_code, 401)

        signed_retry = self._signed_worker_post(
            f"/api/jobs/{signed_create.data['id']}/retry/",
            {},
            secret=secret,
            key_id="worker-jobs-scope",
        )
        self.assertEqual(signed_retry.status_code, 403)

        unsigned_dedupe = self.client.post(
            "/api/jobs/attachments/dedupe-check/",
            {"source_signature": "x", "content_hash": "a" * 64},
            format="json",
        )
        self.assertEqual(unsigned_dedupe.status_code, 401)

        signed_dedupe = self._signed_worker_post(
            "/api/jobs/attachments/dedupe-check/",
            {"source_signature": "x", "content_hash": "a" * 64},
            secret=secret,
            key_id="worker-jobs-scope",
        )
        self.assertEqual(signed_dedupe.status_code, 403)

    def test_26_booking_timeline_enforces_owner_or_operations_policy(self):
        trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Timeline Policy",
                "origin": "A",
                "destination": "B",
                "service_date": "2026-04-08",
                "pickup_window_start": "2026-04-08T10:00:00Z",
                "pickup_window_end": "2026-04-08T11:00:00Z",
                "timezone_id": "UTC",
                "signup_deadline": "2026-04-08T07:30:00Z",
                "capacity_limit": 4,
                "pricing_model": "flat",
                "fare_cents": 1000,
                "tax_bps": 0,
                "fee_cents": 0,
            },
            format="json",
        )
        self.assertEqual(trip.status_code, 201)

        senior_booking = self.senior_client.post(
            f"/api/trips/{trip.data['id']}/bookings/",
            {"care_priority": 2},
            format="json",
        )
        self.assertEqual(senior_booking.status_code, 201)

        family_denied = self.family_client.get(
            f"/api/trips/bookings/{senior_booking.data['id']}/timeline/"
        )
        owner_allowed = self.senior_client.get(
            f"/api/trips/bookings/{senior_booking.data['id']}/timeline/"
        )
        caregiver_allowed = self.caregiver_client.get(
            f"/api/trips/bookings/{senior_booking.data['id']}/timeline/"
        )
        admin_allowed = self.admin_client.get(
            f"/api/trips/bookings/{senior_booking.data['id']}/timeline/"
        )

        self.assertEqual(family_denied.status_code, 403)
        self.assertEqual(owner_allowed.status_code, 200)
        self.assertEqual(caregiver_allowed.status_code, 200)
        self.assertEqual(admin_allowed.status_code, 200)

    def test_27_worker_heartbeat_mismatch_returns_controlled_conflict(self):
        create_job = self.admin_client.post(
            "/api/jobs/",
            {
                "job_type": "ingest_manifest",
                "trigger_type": "manual",
                "priority": 1,
                "source_path": "/data/incoming/hb.csv",
                "payload_json": {},
                "dedupe_key": "heartbeat-mismatch",
            },
            format="json",
        )
        self.assertEqual(create_job.status_code, 201)

        secret = "heart" * 16
        ApiClientKey.objects.create(
            organization=self.org,
            key_id="worker-heartbeat",
            secret_encrypted=encrypt_text(secret),
            secret_fingerprint=hashlib.sha256(secret.encode("utf-8")).hexdigest(),
            is_active=True,
        )

        claim = self._signed_worker_post(
            "/api/jobs/worker/claim/",
            {"worker_id": "worker-a", "concurrency_limit": 2},
            secret=secret,
            key_id="worker-heartbeat",
        )
        self.assertEqual(claim.status_code, 200)

        mismatch = self._signed_worker_post(
            f"/api/jobs/worker/{claim.data['id']}/heartbeat/",
            {"worker_id": "worker-b"},
            secret=secret,
            key_id="worker-heartbeat",
        )
        self.assertEqual(mismatch.status_code, 409)
        self.assertEqual(mismatch.data["code"], "lease_owner_mismatch")

    def test_27b_worker_complete_fail_require_lease_owner(self):
        secret = "lease-owner" * 8
        ApiClientKey.objects.create(
            organization=self.org,
            key_id="worker-lease-owner",
            secret_encrypted=encrypt_text(secret),
            secret_fingerprint=hashlib.sha256(secret.encode("utf-8")).hexdigest(),
            is_active=True,
        )

        complete_job = self.admin_client.post(
            "/api/jobs/",
            {
                "job_type": "ingest_manifest",
                "trigger_type": "manual",
                "priority": 1,
                "source_path": "/data/incoming/complete.csv",
                "payload_json": {},
                "dedupe_key": "lease-complete",
            },
            format="json",
        )
        self.assertEqual(complete_job.status_code, 201)

        complete_claim = self._signed_worker_post(
            "/api/jobs/worker/claim/",
            {"worker_id": "worker-a", "concurrency_limit": 2},
            secret=secret,
            key_id="worker-lease-owner",
        )
        self.assertEqual(complete_claim.status_code, 200)

        complete_missing_worker = self._signed_worker_post(
            f"/api/jobs/worker/{complete_claim.data['id']}/complete/",
            {},
            secret=secret,
            key_id="worker-lease-owner",
        )
        self.assertEqual(complete_missing_worker.status_code, 400)

        complete_mismatch = self._signed_worker_post(
            f"/api/jobs/worker/{complete_claim.data['id']}/complete/",
            {"worker_id": "worker-b"},
            secret=secret,
            key_id="worker-lease-owner",
        )
        self.assertEqual(complete_mismatch.status_code, 409)
        self.assertEqual(complete_mismatch.data["code"], "lease_owner_mismatch")

        complete_ok = self._signed_worker_post(
            f"/api/jobs/worker/{complete_claim.data['id']}/complete/",
            {"worker_id": "worker-a"},
            secret=secret,
            key_id="worker-lease-owner",
        )
        self.assertEqual(complete_ok.status_code, 200)
        self.assertEqual(
            Job.objects.get(id=complete_claim.data["id"]).status, "success"
        )

        fail_job = self.admin_client.post(
            "/api/jobs/",
            {
                "job_type": "ingest_manifest",
                "trigger_type": "manual",
                "priority": 1,
                "source_path": "/data/incoming/fail.csv",
                "payload_json": {},
                "dedupe_key": "lease-fail",
            },
            format="json",
        )
        self.assertEqual(fail_job.status_code, 201)

        fail_claim = self._signed_worker_post(
            "/api/jobs/worker/claim/",
            {"worker_id": "worker-a", "concurrency_limit": 2},
            secret=secret,
            key_id="worker-lease-owner",
        )
        self.assertEqual(fail_claim.status_code, 200)

        fail_missing_worker = self._signed_worker_post(
            f"/api/jobs/worker/{fail_claim.data['id']}/fail/",
            {"error_message": "missing worker"},
            secret=secret,
            key_id="worker-lease-owner",
        )
        self.assertEqual(fail_missing_worker.status_code, 400)

        fail_mismatch = self._signed_worker_post(
            f"/api/jobs/worker/{fail_claim.data['id']}/fail/",
            {"worker_id": "worker-b", "error_message": "bad lease"},
            secret=secret,
            key_id="worker-lease-owner",
        )
        self.assertEqual(fail_mismatch.status_code, 409)
        self.assertEqual(fail_mismatch.data["code"], "lease_owner_mismatch")

        fail_ok = self._signed_worker_post(
            f"/api/jobs/worker/{fail_claim.data['id']}/fail/",
            {"worker_id": "worker-a", "error_message": "worker reported failure"},
            secret=secret,
            key_id="worker-lease-owner",
        )
        self.assertEqual(fail_ok.status_code, 200)
        failed_job_state = Job.objects.get(id=fail_claim.data["id"])
        self.assertEqual(failed_job_state.attempt_count, 1)
        self.assertEqual(failed_job_state.status, "pending")

    def test_28_api_key_commands_mask_secret_by_default(self):
        create_out = StringIO()
        create_err = StringIO()
        call_command(
            "create_api_key",
            "HARBOR_TEST",
            "cli-create-key",
            stdout=create_out,
            stderr=create_err,
        )
        output = create_out.getvalue()
        self.assertIn("secret=", output)
        self.assertIn("...", output)
        self.assertNotIn("Warning: revealing raw secret", create_err.getvalue())

        reveal_out = StringIO()
        reveal_err = StringIO()
        call_command(
            "rotate_api_key",
            "cli-create-key",
            "--reveal-secret",
            stdout=reveal_out,
            stderr=reveal_err,
        )
        self.assertIn("Warning: revealing raw secret", reveal_err.getvalue())
        self.assertIn("secret=", reveal_out.getvalue())

    def test_29_reack_required_blocks_rider_actions_until_acknowledged(self):
        trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Reack Action Gate",
                "origin": "A",
                "destination": "B",
                "service_date": "2026-04-09",
                "pickup_window_start": "2030-04-09T10:00:00Z",
                "pickup_window_end": "2030-04-09T11:00:00Z",
                "timezone_id": "UTC",
                "signup_deadline": "2030-04-09T07:30:00Z",
                "capacity_limit": 3,
                "pricing_model": "flat",
                "fare_cents": 1000,
                "tax_bps": 0,
                "fee_cents": 0,
                "cancellation_cutoff_minutes": 0,
            },
            format="json",
        )
        booking = self.senior_client.post(
            f"/api/trips/{trip.data['id']}/bookings/",
            {"care_priority": 1},
            format="json",
        )
        self.assertEqual(booking.status_code, 201)

        update = self.admin_client.patch(
            f"/api/trips/{trip.data['id']}/",
            {"fare_cents": 1200, "change_summary": "Fare update"},
            format="json",
        )
        self.assertEqual(update.status_code, 200)

        blocked_cancel = self.senior_client.post(
            f"/api/trips/bookings/{booking.data['id']}/cancel/",
            {"reason": "Need to cancel"},
            format="json",
        )
        blocked_refund = self.senior_client.post(
            f"/api/trips/bookings/{booking.data['id']}/refund-request/",
            {"reason": "Need refund"},
            format="json",
        )
        self.assertEqual(blocked_cancel.status_code, 409)
        self.assertEqual(blocked_refund.status_code, 409)

        acknowledged = self.senior_client.post(
            f"/api/trips/bookings/{booking.data['id']}/ack/",
            {},
            format="json",
        )
        self.assertEqual(acknowledged.status_code, 200)
        self.assertFalse(acknowledged.data["reack_required"])

        allowed_cancel = self.senior_client.post(
            f"/api/trips/bookings/{booking.data['id']}/cancel/",
            {"reason": "Need to cancel"},
            format="json",
        )
        self.assertEqual(allowed_cancel.status_code, 200)

    def test_30_jobs_list_pagination_and_sort_boundaries(self):
        for idx, priority in enumerate([3, 1, 2], start=1):
            self.admin_client.post(
                "/api/jobs/",
                {
                    "job_type": f"ingest_{idx}",
                    "trigger_type": "manual",
                    "priority": priority,
                    "source_path": f"/tmp/{idx}.csv",
                    "payload_json": {},
                    "dedupe_key": f"sort-{idx}",
                },
                format="json",
            )

        paged = self.admin_client.get(
            "/api/jobs/?sort_by=priority&sort_order=asc&limit=2&offset=0"
        )
        self.assertEqual(paged.status_code, 200)
        self.assertEqual(len(paged.data), 2)
        self.assertLessEqual(paged.data[0]["priority"], paged.data[1]["priority"])

        invalid_limit = self.admin_client.get("/api/jobs/?limit=0")
        invalid_sort = self.admin_client.get("/api/jobs/?sort_by=status")
        self.assertEqual(invalid_limit.status_code, 400)
        self.assertEqual(invalid_sort.status_code, 400)

    def test_31_favorites_and_comparisons_duplicate_conflicts(self):
        favorite_1 = self.senior_client.post(
            "/api/auth/favorites/",
            {"kind": "trip", "reference_id": "dup-trip"},
            format="json",
        )
        favorite_2 = self.senior_client.post(
            "/api/auth/favorites/",
            {"kind": "trip", "reference_id": "dup-trip"},
            format="json",
        )
        self.assertEqual(favorite_1.status_code, 201)
        self.assertEqual(favorite_2.status_code, 409)

        comparison_1 = self.senior_client.post(
            "/api/auth/comparisons/",
            {"kind": "plan", "reference_id": "dup-plan"},
            format="json",
        )
        comparison_2 = self.senior_client.post(
            "/api/auth/comparisons/",
            {"kind": "plan", "reference_id": "dup-plan"},
            format="json",
        )
        self.assertEqual(comparison_1.status_code, 201)
        self.assertEqual(comparison_2.status_code, 409)

    def test_32_verification_document_upload_open_and_validation(self):
        req_resp = self.senior_client.post(
            "/api/auth/verification-requests/",
            {
                "is_high_risk": False,
                "attestation": "Upload docs",
            },
            format="json",
        )
        self.assertEqual(req_resp.status_code, 201)

        good_file = SimpleUploadedFile(
            "id.png",
            b"\x89PNG\r\n\x1a\nsmallpng",
            content_type="image/png",
        )
        upload = self.senior_client.post(
            f"/api/auth/verification-requests/{req_resp.data['id']}/documents/upload/",
            {
                "document_type": "government_id",
                "uploaded_file": good_file,
            },
            format="multipart",
        )
        self.assertEqual(upload.status_code, 201, upload.data)
        self.assertTrue(upload.data["documents"])
        doc_id = upload.data["documents"][0]["id"]

        open_doc = self.admin_client.get(
            f"/api/auth/verification-documents/{doc_id}/open/"
        )
        self.assertEqual(open_doc.status_code, 200)

        bad_mime = SimpleUploadedFile(
            "bad.txt",
            b"not allowed",
            content_type="text/plain",
        )
        bad_upload = self.senior_client.post(
            f"/api/auth/verification-requests/{req_resp.data['id']}/documents/upload/",
            {
                "document_type": "other",
                "uploaded_file": bad_mime,
            },
            format="multipart",
        )
        self.assertEqual(bad_upload.status_code, 400)

    def test_33_masked_sensitive_fields_and_authorized_reveal(self):
        create_profile = self.admin_client.post(
            "/api/auth/traveler-profiles/",
            {
                "display_name": "Gov Profile",
                "identifier": "TRAVEL-99990000",
                "government_id": "GOV-77776666",
                "credential_number": "CRED-55554444",
            },
            format="json",
        )
        self.assertEqual(create_profile.status_code, 201)
        self.assertTrue(create_profile.data["masked_government_id"].endswith("6666"))
        self.assertNotIn("government_id", create_profile.data)

        profile_id = create_profile.data["id"]
        unauthorized = self.senior_client.get(
            f"/api/security/traveler-profiles/{profile_id}/reveal/government-id/"
        )
        self.assertEqual(unauthorized.status_code, 403)

        session = self.admin_client.post(
            "/api/security/unmask-sessions/",
            {
                "field_name": f"traveler_government_id:{profile_id}",
                "reason": "identity check",
                "minutes": 5,
            },
            format="json",
        )
        self.assertEqual(session.status_code, 201)

        reveal = self.admin_client.get(
            f"/api/security/traveler-profiles/{profile_id}/reveal/government-id/"
        )
        self.assertEqual(reveal.status_code, 200)
        self.assertEqual(reveal.data["government_id"], "GOV-77776666")

    def test_34_offline_folder_ingest_resumes_from_checkpoint_after_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            csv_path = tmp_path / "manifest.csv"
            csv_path.write_text(
                "rider_id,trip_id\n100,200\n,201\n",
                encoding="utf-8",
            )
            (tmp_path / "id-card.png").write_bytes(b"\x89PNG\r\n\x1a\nattachment")

            job = Job.objects.create(
                organization=self.org,
                job_type="ingest.folder_scan",
                source_path=str(tmp_path),
                payload_json={},
                trigger_type="manual",
                priority=1,
                dedupe_key="checkpoint-resume",
                created_by=self.org_admin,
            )

            with self.assertRaises(RuntimeError):
                run_folder_ingest_job(job, fail_after_rows=1)

            job.refresh_from_db()
            self.assertEqual(job.status, "pending")
            self.assertEqual(job.attempt_count, 1)
            cp = JobCheckpoint.objects.get(job=job, file_name="manifest.csv")
            self.assertEqual(cp.row_offset, 1)

            stats = run_folder_ingest_job(job)
            job.refresh_from_db()
            cp.refresh_from_db()

            self.assertEqual(job.status, "success")
            self.assertEqual(cp.row_offset, 2)
            self.assertEqual(stats["row_errors"], 1)
            self.assertEqual(job.row_errors.count(), 1)
            self.assertTrue(
                IngestAttachmentFingerprint.objects.filter(
                    organization=self.org,
                    first_seen_job=job,
                ).exists()
            )

    def test_35_platform_admin_cross_org_oversight_and_org_admin_denial(self):
        trip = self.platform_admin_client.post(
            "/api/trips/",
            {
                "organization_id": self.other_org.id,
                "title": "Cross Org Trip",
                "origin": "A",
                "destination": "B",
                "service_date": "2026-05-01",
                "pickup_window_start": "2026-05-01T10:00:00Z",
                "pickup_window_end": "2026-05-01T11:00:00Z",
                "timezone_id": "UTC",
                "signup_deadline": "2026-05-01T07:30:00Z",
                "capacity_limit": 4,
                "pricing_model": "flat",
                "fare_cents": 1000,
                "tax_bps": 0,
                "fee_cents": 0,
            },
            format="json",
        )
        self.assertEqual(trip.status_code, 201)

        wh = self.platform_admin_client.post(
            "/api/warehouses/",
            {
                "organization_id": self.other_org.id,
                "name": "Cross Org Warehouse",
                "region": "West",
            },
            format="json",
        )
        self.assertEqual(wh.status_code, 201)

        plan = self.platform_admin_client.post(
            "/api/inventory/plans/",
            {
                "organization_id": self.other_org.id,
                "title": "Cross Org Plan",
                "region": "West",
                "asset_type": "Medical",
                "mode": "full",
            },
            format="json",
        )
        self.assertEqual(plan.status_code, 201)

        job = self.platform_admin_client.post(
            "/api/jobs/",
            {
                "organization_id": self.other_org.id,
                "job_type": "ingest_manifest",
                "trigger_type": "manual",
                "priority": 2,
                "source_path": "/tmp/cross.csv",
                "payload_json": {},
                "dedupe_key": "platform-cross-org",
            },
            format="json",
        )
        self.assertEqual(job.status_code, 201)

        alert = AnomalyAlert.objects.create(
            organization=self.other_org,
            title="Cross Org Alert",
            alert_type="security",
            severity="warning",
            details="Cross org visibility",
        )

        platform_trips = self.platform_admin_client.get(
            f"/api/trips/?organization_id={self.other_org.id}"
        )
        platform_wh = self.platform_admin_client.get(
            f"/api/warehouses/?organization_id={self.other_org.id}"
        )
        platform_plans = self.platform_admin_client.get(
            f"/api/inventory/plans/?organization_id={self.other_org.id}"
        )
        platform_jobs = self.platform_admin_client.get(
            f"/api/jobs/?organization_id={self.other_org.id}"
        )
        platform_alerts = self.platform_admin_client.get(
            f"/api/monitoring/alerts/?organization_id={self.other_org.id}"
        )

        self.assertEqual(platform_trips.status_code, 200)
        self.assertEqual(platform_wh.status_code, 200)
        self.assertEqual(platform_plans.status_code, 200)
        self.assertEqual(platform_jobs.status_code, 200)
        self.assertEqual(platform_alerts.status_code, 200)
        self.assertTrue(
            any(item["id"] == trip.data["id"] for item in platform_trips.data)
        )
        self.assertTrue(any(item["id"] == wh.data["id"] for item in platform_wh.data))
        self.assertTrue(
            any(item["id"] == plan.data["id"] for item in platform_plans.data)
        )
        self.assertTrue(
            any(item["id"] == job.data["id"] for item in platform_jobs.data)
        )
        self.assertTrue(any(item["id"] == alert.id for item in platform_alerts.data))

        org_admin_trips = self.admin_client.get(
            f"/api/trips/?organization_id={self.other_org.id}"
        )
        org_admin_wh = self.admin_client.get(
            f"/api/warehouses/?organization_id={self.other_org.id}"
        )
        org_admin_plans = self.admin_client.get(
            f"/api/inventory/plans/?organization_id={self.other_org.id}"
        )
        org_admin_jobs = self.admin_client.get(
            f"/api/jobs/?organization_id={self.other_org.id}"
        )
        org_admin_alerts = self.admin_client.get(
            f"/api/monitoring/alerts/?organization_id={self.other_org.id}"
        )

        self.assertEqual(org_admin_trips.status_code, 200)
        self.assertEqual(org_admin_wh.status_code, 200)
        self.assertEqual(org_admin_plans.status_code, 200)
        self.assertEqual(org_admin_jobs.status_code, 200)
        self.assertEqual(org_admin_alerts.status_code, 200)
        self.assertFalse(
            any(item["id"] == trip.data["id"] for item in org_admin_trips.data)
        )
        self.assertFalse(any(item["id"] == wh.data["id"] for item in org_admin_wh.data))
        self.assertFalse(
            any(item["id"] == plan.data["id"] for item in org_admin_plans.data)
        )
        self.assertFalse(
            any(item["id"] == job.data["id"] for item in org_admin_jobs.data)
        )
        self.assertFalse(any(item["id"] == alert.id for item in org_admin_alerts.data))

    def test_35b_cross_tenant_mutation_and_sensitive_reads_are_denied(self):
        trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Tenant Isolation",
                "origin": "A",
                "destination": "B",
                "service_date": "2026-05-03",
                "pickup_window_start": "2026-05-03T10:00:00Z",
                "pickup_window_end": "2026-05-03T11:00:00Z",
                "timezone_id": "UTC",
                "signup_deadline": "2026-05-03T07:30:00Z",
                "capacity_limit": 4,
                "pricing_model": "flat",
                "fare_cents": 1000,
                "tax_bps": 0,
                "fee_cents": 0,
            },
            format="json",
        )
        booking = self.senior_client.post(
            f"/api/trips/{trip.data['id']}/bookings/",
            {"care_priority": 1},
            format="json",
        )
        self.assertEqual(booking.status_code, 201)

        verification = self.senior_client.post(
            "/api/auth/verification-requests/",
            {"attestation_text": "cross-org isolation test", "is_high_risk": False},
            format="json",
        )
        self.assertEqual(verification.status_code, 201)

        upload = SimpleUploadedFile("id.png", b"img", content_type="image/png")
        upload_resp = self.senior_client.post(
            f"/api/auth/verification-requests/{verification.data['id']}/documents/upload/",
            {"document_type": "government_id", "uploaded_file": upload},
            format="multipart",
        )
        self.assertEqual(upload_resp.status_code, 201)
        doc_id = upload_resp.data["documents"][0]["id"]

        profile = self.admin_client.post(
            "/api/auth/traveler-profiles/",
            {
                "display_name": "Tenant Sensitive",
                "identifier": "TENANT-12345678",
                "government_id": "GOV-87654321",
            },
            format="json",
        )
        self.assertEqual(profile.status_code, 201)

        export_req = self.senior_client.post(
            "/api/auth/exports/request/",
            {"format": "json", "include_unmasked": False},
            format="json",
        )
        self.assertEqual(export_req.status_code, 201)
        call_command("process_exports", "--limit", "10")

        cross_cancel = self.other_admin_client.post(
            f"/api/trips/bookings/{booking.data['id']}/cancel/",
            {"reason": "cross org"},
            format="json",
        )
        self.assertIn(cross_cancel.status_code, {403, 404})

        cross_refund = self.other_admin_client.post(
            f"/api/trips/bookings/{booking.data['id']}/refund-request/",
            {"reason": "cross org"},
            format="json",
        )
        self.assertIn(cross_refund.status_code, {403, 404})

        cross_doc_open = self.other_admin_client.get(
            f"/api/auth/verification-documents/{doc_id}/open/"
        )
        self.assertEqual(cross_doc_open.status_code, 404)

        cross_reveal = self.other_admin_client.get(
            f"/api/security/traveler-profiles/{profile.data['id']}/reveal/"
        )
        self.assertEqual(cross_reveal.status_code, 404)

        cross_export_download = self.other_admin_client.get(
            f"/api/auth/exports/{export_req.data['id']}/download/"
        )
        self.assertIn(cross_export_download.status_code, {403, 404})

    def test_36_crypto_requires_explicit_key_and_valid_key_encrypts(self):
        from core.crypto import decrypt_text, encrypt_text

        previous = os.environ.pop("APP_AES256_KEY_B64", None)
        try:
            with self.assertRaises(ValueError):
                encrypt_text("hello")
        finally:
            if previous is not None:
                os.environ["APP_AES256_KEY_B64"] = previous

        os.environ["APP_AES256_KEY_B64"] = (
            "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
        )
        token = encrypt_text("hello")
        self.assertNotEqual(token, "hello")
        self.assertEqual(decrypt_text(token), "hello")

    def test_37_backup_command_rejects_weak_passphrase_and_allows_secure(self):
        from unittest.mock import patch

        os.environ["BACKUP_PASSPHRASE"] = "change-me"
        with self.assertRaises(CommandError):
            call_command("backup_db")

        os.environ["BACKUP_PASSPHRASE"] = "really-strong-passphrase-2026"
        with tempfile.TemporaryDirectory() as backup_dir:
            with (
                patch("core.management.commands.backup_db.subprocess.run") as run_mock,
                override_settings(BACKUP_DIR=backup_dir),
            ):
                run_mock.return_value = None
                call_command("backup_db")
                self.assertGreaterEqual(run_mock.call_count, 2)

    def test_38_password_policy_negative_cases(self):
        client = APIClient()
        short = client.post(
            "/api/auth/register/",
            {
                "organization_code": "HARBOR_TEST",
                "username": "short_pass_user",
                "password": "Aa1short",
                "real_name": "Short",
            },
            format="json",
        )
        no_number = client.post(
            "/api/auth/register/",
            {
                "organization_code": "HARBOR_TEST",
                "username": "no_number_user",
                "password": "PasswordOnlyAA",
                "real_name": "No Number",
            },
            format="json",
        )
        no_letter = client.post(
            "/api/auth/register/",
            {
                "organization_code": "HARBOR_TEST",
                "username": "no_letter_user",
                "password": "123456789012",
                "real_name": "No Letter",
            },
            format="json",
        )
        self.assertEqual(short.status_code, 400)
        self.assertEqual(no_number.status_code, 400)
        self.assertEqual(no_letter.status_code, 400)

    def test_39_csrf_rejects_mutating_session_request_without_token(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.senior)
        resp = client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_40_trip_signup_deadline_invalid_boundary_rejected(self):
        resp = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Boundary Trip",
                "origin": "A",
                "destination": "B",
                "service_date": "2026-06-01",
                "pickup_window_start": "2026-06-01T10:00:00Z",
                "pickup_window_end": "2026-06-01T11:00:00Z",
                "timezone_id": "UTC",
                "signup_deadline": "2026-06-01T08:01:00Z",
                "capacity_limit": 3,
                "pricing_model": "flat",
                "fare_cents": 1000,
                "tax_bps": 0,
                "fee_cents": 0,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_41_logs_do_not_leak_passwords_or_signing_secrets(self):
        with self.assertLogs("harborops.audit", level="INFO") as captured:
            self.senior_client.post(
                "/api/auth/login/",
                {"username": "senior_test", "password": "WrongPass1234"},
                format="json",
            )

        joined = "\n".join(captured.output)
        self.assertNotIn("WrongPass1234", joined)
        self.assertNotIn("password", joined.lower())

    def test_42_security_config_command_validates_key_presence_and_format(self):
        tracked_vars = {
            "APP_AES256_KEY_B64": os.environ.get("APP_AES256_KEY_B64"),
            "DJANGO_SECRET_KEY": os.environ.get("DJANGO_SECRET_KEY"),
            "MYSQL_PASSWORD": os.environ.get("MYSQL_PASSWORD"),
            "MYSQL_ROOT_PASSWORD": os.environ.get("MYSQL_ROOT_PASSWORD"),
            "DB_ADMIN_PASSWORD": os.environ.get("DB_ADMIN_PASSWORD"),
            "BACKUP_PASSPHRASE": os.environ.get("BACKUP_PASSPHRASE"),
        }
        try:
            os.environ["DJANGO_SECRET_KEY"] = "valid-test-django-secret-key-1234567890"
            os.environ["MYSQL_PASSWORD"] = "valid-test-db-password-12345"
            os.environ["MYSQL_ROOT_PASSWORD"] = "valid-test-root-password-12345"
            os.environ["DB_ADMIN_PASSWORD"] = "valid-test-root-password-12345"
            os.environ["BACKUP_PASSPHRASE"] = "valid-test-backup-passphrase-12345"

            os.environ.pop("APP_AES256_KEY_B64", None)
            with self.assertRaises(CommandError):
                call_command("check_security_config")

            os.environ["APP_AES256_KEY_B64"] = "not-base64"
            with self.assertRaises(CommandError):
                call_command("check_security_config")

            os.environ["APP_AES256_KEY_B64"] = "YWJj"
            with self.assertRaises(CommandError):
                call_command("check_security_config")

            os.environ["APP_AES256_KEY_B64"] = (
                "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
            )
            with self.assertRaises(CommandError):
                call_command("check_security_config")

            os.environ["APP_AES256_KEY_B64"] = (
                "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmM0MjA="
            )
            call_command("check_security_config")
        finally:
            for key, value in tracked_vars.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_43_startup_fails_for_missing_or_default_aes_key(self):
        backend_dir = Path(__file__).resolve().parents[1]
        base_env = os.environ.copy()

        missing_env = dict(base_env)
        missing_env.pop("APP_AES256_KEY_B64", None)
        missing = subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=backend_dir,
            env=missing_env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn(
            "APP_AES256_KEY_B64 is required",
            f"{missing.stdout}\n{missing.stderr}",
        )

        default_env = dict(base_env)
        default_env["APP_AES256_KEY_B64"] = (
            "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
        )
        insecure_default = subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=backend_dir,
            env=default_env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(insecure_default.returncode, 0)
        self.assertIn(
            "uses an insecure default value",
            f"{insecure_default.stdout}\n{insecure_default.stderr}",
        )

    def test_44_startup_succeeds_with_valid_32_byte_aes_key(self):
        backend_dir = Path(__file__).resolve().parents[1]
        valid_env = os.environ.copy()
        valid_env["APP_AES256_KEY_B64"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmM0MjA="
        valid_env["DJANGO_SECRET_KEY"] = "not-placeholder-secret-value-123456789"
        valid_env["APP_RUNTIME_PROFILE"] = "production"
        valid_env["DJANGO_DEBUG"] = "false"
        valid_env["MYSQL_PASSWORD"] = "valid-prod-db-password-12345"
        valid_env["MYSQL_ROOT_PASSWORD"] = "valid-prod-root-password-12345"
        valid_env["DB_ADMIN_PASSWORD"] = "valid-prod-root-password-12345"
        valid_env["BACKUP_PASSPHRASE"] = "valid-prod-backup-passphrase-12345"
        valid = subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=backend_dir,
            env=valid_env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(valid.returncode, 0)
        self.assertIn("System check identified no issues", valid.stdout)

    def test_45_worker_runtime_path_enforces_per_org_concurrency_limit(self):
        command = OfflineIngestWorkerCommand()
        for idx in range(3):
            running = Job.objects.create(
                organization=self.org,
                job_type="ingest.folder_scan",
                source_path=f"/tmp/running-{idx}",
                payload_json={},
                trigger_type="manual",
                priority=1,
                dedupe_key=f"running-{idx}",
                status=JobStatus.RUNNING,
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
            source_path="/tmp/pending",
            payload_json={},
            trigger_type="manual",
            priority=1,
            dedupe_key="pending-concurrency-blocked",
            status=JobStatus.PENDING,
        )

        claimed = command._next_pending_jobs()
        self.assertEqual(claimed, [])
        pending.refresh_from_db()
        self.assertEqual(pending.status, JobStatus.PENDING)

    def test_46_worker_runtime_path_blocks_dependencies_until_prereq_success(self):
        command = OfflineIngestWorkerCommand()

        prerequisite = Job.objects.create(
            organization=self.org,
            job_type="ingest.folder_scan",
            source_path="/tmp/prerequisite",
            payload_json={},
            trigger_type="manual",
            priority=5,
            dedupe_key="dep-prerequisite",
            status=JobStatus.PENDING,
        )
        dependent = Job.objects.create(
            organization=self.org,
            job_type="ingest.folder_scan",
            source_path="/tmp/dependent",
            payload_json={},
            trigger_type="manual",
            priority=1,
            dedupe_key="dep-dependent",
            status=JobStatus.PENDING,
        )
        JobDependency.objects.create(job=dependent, depends_on=prerequisite)

        first_claim = command._next_pending_jobs()
        self.assertEqual(first_claim, [])
        dependent.refresh_from_db()
        self.assertEqual(dependent.status, JobStatus.BLOCKED)

        second_claim = command._next_pending_jobs()
        self.assertEqual(len(second_claim), 1)
        self.assertEqual(second_claim[0].id, prerequisite.id)
        self.assertEqual(second_claim[0].status, JobStatus.RUNNING)

        mark_job_success(second_claim[0])

        third_claim = command._next_pending_jobs()
        self.assertEqual(len(third_claim), 1)
        self.assertEqual(third_claim[0].id, dependent.id)
        self.assertEqual(third_claim[0].status, JobStatus.RUNNING)

    def test_47_startup_fails_with_debug_enabled_outside_dev_profile(self):
        backend_dir = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["APP_AES256_KEY_B64"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmM0MjA="
        env["DJANGO_SECRET_KEY"] = "not-placeholder-secret-value-123456789"
        env["MYSQL_PASSWORD"] = "valid-prod-db-password-12345"
        env["MYSQL_ROOT_PASSWORD"] = "valid-prod-root-password-12345"
        env["DB_ADMIN_PASSWORD"] = "valid-prod-root-password-12345"
        env["BACKUP_PASSPHRASE"] = "valid-prod-backup-passphrase-12345"
        env["DJANGO_DEBUG"] = "true"
        env["APP_RUNTIME_PROFILE"] = "production"

        result = subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "DJANGO_DEBUG=true is only allowed",
            f"{result.stdout}\n{result.stderr}",
        )

    def test_48_startup_allows_debug_enabled_in_explicit_dev_profile(self):
        backend_dir = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["APP_AES256_KEY_B64"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmM0MjA="
        env["DJANGO_SECRET_KEY"] = "not-placeholder-secret-value-123456789"
        env["MYSQL_PASSWORD"] = "valid-prod-db-password-12345"
        env["MYSQL_ROOT_PASSWORD"] = "valid-prod-root-password-12345"
        env["DB_ADMIN_PASSWORD"] = "valid-prod-root-password-12345"
        env["BACKUP_PASSPHRASE"] = "valid-prod-backup-passphrase-12345"
        env["DJANGO_DEBUG"] = "true"
        env["APP_RUNTIME_PROFILE"] = "dev"

        result = subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("System check identified no issues", result.stdout)

    def test_49_startup_fails_without_django_secret_key(self):
        backend_dir = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["APP_AES256_KEY_B64"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmM0MjA="
        env["MYSQL_PASSWORD"] = "valid-prod-db-password-12345"
        env["MYSQL_ROOT_PASSWORD"] = "valid-prod-root-password-12345"
        env["DB_ADMIN_PASSWORD"] = "valid-prod-root-password-12345"
        env["BACKUP_PASSPHRASE"] = "valid-prod-backup-passphrase-12345"
        env["APP_RUNTIME_PROFILE"] = "production"
        env["DJANGO_DEBUG"] = "false"
        env.pop("DJANGO_SECRET_KEY", None)

        result = subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "DJANGO_SECRET_KEY is required", f"{result.stdout}\n{result.stderr}"
        )
