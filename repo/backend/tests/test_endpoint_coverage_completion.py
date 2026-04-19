"""No-mock API coverage for endpoints previously uncovered by the test suite.

Every test in this module drives an HTTP request through the real URL router
and view pipeline using DRF's APIClient. No mocks or patches are used.
"""

import os

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from access.models import BaseRole, Role
from accounts.models import (
    AccountDeletionRequest,
    DataExportRequest,
    TravelerProfile,
    User,
    UserPreference,
    UserRole,
)
from inventory.models import CorrectiveAction, InventoryCountLine
from jobs.models import Job, JobCheckpoint, JobFailure, JobStatus
from organizations.models import Organization


class EndpointCoverageCompletionSuite(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._previous_aes_key = os.environ.get("APP_AES256_KEY_B64")
        os.environ["APP_AES256_KEY_B64"] = (
            "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
        )

        cls.org = Organization.objects.create(
            name="Coverage Test Org", code="COV_TEST"
        )
        call_command("bootstrap_access")

        cls.admin_user = User.objects.create_user(
            username="cov_admin",
            password="SecurePass1234",
            organization=cls.org,
            real_name="Coverage Admin",
            is_staff=True,
        )
        cls.senior_user = User.objects.create_user(
            username="cov_senior",
            password="SecurePass1234",
            organization=cls.org,
            real_name="Coverage Senior",
        )
        cls._assign_role(cls.admin_user, BaseRole.ORG_ADMIN)
        cls._assign_role(cls.senior_user, BaseRole.SENIOR)

        cls.admin_client = APIClient()
        cls.admin_client.force_login(cls.admin_user)
        cls.senior_client = APIClient()
        cls.senior_client.force_login(cls.senior_user)

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

    # --- Core / access ---

    def test_health_check_returns_ok(self):
        resp = APIClient().get("/api/health/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "ok")

    def test_my_roles_returns_assigned_roles(self):
        resp = self.admin_client.get("/api/access/me/roles/")
        self.assertEqual(resp.status_code, 200)
        codes = {role["code"] for role in resp.data}
        self.assertIn(BaseRole.ORG_ADMIN, codes)

    # --- Accounts: change password / preferences / traveler profiles ---

    def test_change_password_flow_rotates_credentials(self):
        resp = self.senior_client.post(
            "/api/auth/change-password/",
            {
                "current_password": "SecurePass1234",
                "new_password": "BrandNewPass9876",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.senior_user.refresh_from_db()
        self.assertTrue(self.senior_user.check_password("BrandNewPass9876"))

    def test_preferences_get_and_put_roundtrip(self):
        get_resp = self.admin_client.get("/api/auth/preferences/")
        self.assertEqual(get_resp.status_code, 200)

        put_resp = self.admin_client.put(
            "/api/auth/preferences/",
            {
                "locale": "en-US",
                "timezone": "America/Chicago",
                "large_text_mode": True,
                "high_contrast_mode": False,
            },
            format="json",
        )
        self.assertEqual(put_resp.status_code, 200)
        self.assertTrue(put_resp.data["large_text_mode"])
        self.assertEqual(put_resp.data["timezone"], "America/Chicago")

        persisted = UserPreference.objects.get(user=self.admin_user)
        self.assertTrue(persisted.large_text_mode)

    def test_traveler_profile_list_and_put_update(self):
        create_resp = self.admin_client.post(
            "/api/auth/traveler-profiles/",
            {
                "display_name": "Primary",
                "identifier": "TRV-1",
                "government_id": "GOV-1",
                "credential_number": "CRED-1",
            },
            format="json",
        )
        self.assertEqual(create_resp.status_code, 201)
        profile_id = create_resp.data["id"]

        list_resp = self.admin_client.get("/api/auth/traveler-profiles/")
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(len(list_resp.data), 1)

        put_resp = self.admin_client.put(
            f"/api/auth/traveler-profiles/{profile_id}/",
            {"display_name": "Primary Renamed"},
            format="json",
        )
        self.assertEqual(put_resp.status_code, 200)
        self.assertEqual(put_resp.data["display_name"], "Primary Renamed")

        missing_resp = self.admin_client.put(
            "/api/auth/traveler-profiles/999999/",
            {"display_name": "x"},
            format="json",
        )
        self.assertEqual(missing_resp.status_code, 404)

    def test_account_deletion_request_created_and_user_deactivated(self):
        doomed = User.objects.create_user(
            username="cov_doomed",
            password="SecurePass1234",
            organization=self.org,
            real_name="Doomed",
        )
        self._assign_role(doomed, BaseRole.FAMILY_MEMBER)
        client = APIClient()
        client.force_login(doomed)

        resp = client.post(
            "/api/auth/deletion-request/",
            {"retention_notice": "Account cleanup requested."},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        doomed.refresh_from_db()
        self.assertFalse(doomed.is_active)
        self.assertTrue(
            AccountDeletionRequest.objects.filter(user=doomed).exists()
        )

    def test_exports_list_returns_users_own_requests(self):
        create_resp = self.admin_client.post(
            "/api/auth/exports/request/",
            {"include_unmasked": False, "format": "json"},
            format="json",
        )
        self.assertEqual(create_resp.status_code, 201)

        list_resp = self.admin_client.get("/api/auth/exports/")
        self.assertEqual(list_resp.status_code, 200)
        ids = [item["id"] for item in list_resp.data]
        self.assertIn(create_resp.data["id"], ids)

    # --- Warehouses: full CRUD coverage ---

    def _create_warehouse_tree(self):
        wh = self.admin_client.post(
            "/api/warehouses/",
            {"name": "CoverageWH", "region": "East"},
            format="json",
        )
        self.assertEqual(wh.status_code, 201)
        zone = self.admin_client.post(
            "/api/warehouses/zones/",
            {
                "warehouse": wh.data["id"],
                "name": "CoverageZone",
                "temperature_zone": "ambient",
                "hazmat_class": "none",
            },
            format="json",
        )
        self.assertEqual(zone.status_code, 201)
        loc = self.admin_client.post(
            "/api/warehouses/locations/",
            {
                "zone": zone.data["id"],
                "code": "COV-L1",
                "capacity_limit": "50.00",
                "capacity_unit": "units",
            },
            format="json",
        )
        self.assertEqual(loc.status_code, 201)
        partner = self.admin_client.post(
            "/api/warehouses/partners/",
            {
                "partner_type": "supplier",
                "external_code": "COV-SUP",
                "display_name": "Coverage Supplier",
                "effective_start": "2026-01-01",
                "effective_end": "2026-12-31",
                "data_json": {"tier": 1},
            },
            format="json",
        )
        self.assertEqual(partner.status_code, 201)
        return wh.data["id"], zone.data["id"], loc.data["id"], partner.data["id"]

    def test_warehouse_zone_location_partner_list_put_delete(self):
        wh_id, zone_id, loc_id, partner_id = self._create_warehouse_tree()

        zones_list = self.admin_client.get("/api/warehouses/zones/")
        self.assertEqual(zones_list.status_code, 200)
        self.assertTrue(any(z["id"] == zone_id for z in zones_list.data))

        locs_list = self.admin_client.get("/api/warehouses/locations/")
        self.assertEqual(locs_list.status_code, 200)
        self.assertTrue(any(l["id"] == loc_id for l in locs_list.data))

        partners_list = self.admin_client.get("/api/warehouses/partners/")
        self.assertEqual(partners_list.status_code, 200)
        self.assertTrue(any(p["id"] == partner_id for p in partners_list.data))

        wh_put = self.admin_client.put(
            f"/api/warehouses/{wh_id}/",
            {"name": "CoverageWH Renamed"},
            format="json",
        )
        self.assertEqual(wh_put.status_code, 200)
        self.assertEqual(wh_put.data["name"], "CoverageWH Renamed")

        zone_put = self.admin_client.put(
            f"/api/warehouses/zones/{zone_id}/",
            {"name": "ZoneRenamed"},
            format="json",
        )
        self.assertEqual(zone_put.status_code, 200)
        self.assertEqual(zone_put.data["name"], "ZoneRenamed")

        loc_put = self.admin_client.put(
            f"/api/warehouses/locations/{loc_id}/",
            {"capacity_limit": "75.00"},
            format="json",
        )
        self.assertEqual(loc_put.status_code, 200)

        partner_put = self.admin_client.put(
            f"/api/warehouses/partners/{partner_id}/",
            {"display_name": "Coverage Supplier Renamed"},
            format="json",
        )
        self.assertEqual(partner_put.status_code, 200)
        self.assertEqual(partner_put.data["display_name"], "Coverage Supplier Renamed")

        # Delete order: partner, location, zone, warehouse
        self.assertEqual(
            self.admin_client.delete(
                f"/api/warehouses/partners/{partner_id}/"
            ).status_code,
            204,
        )
        self.assertEqual(
            self.admin_client.delete(
                f"/api/warehouses/locations/{loc_id}/"
            ).status_code,
            204,
        )
        self.assertEqual(
            self.admin_client.delete(
                f"/api/warehouses/zones/{zone_id}/"
            ).status_code,
            204,
        )
        self.assertEqual(
            self.admin_client.delete(f"/api/warehouses/{wh_id}/").status_code, 204
        )

        # Subsequent delete returns 404
        self.assertEqual(
            self.admin_client.delete(f"/api/warehouses/{wh_id}/").status_code, 404
        )

    # --- Inventory plan/task/line list, patch, delete, acknowledge-action ---

    def test_inventory_plan_task_line_list_patch_delete_and_acknowledge(self):
        wh = self.admin_client.post(
            "/api/warehouses/", {"name": "InvCov", "region": "Mid"}, format="json"
        )
        zone = self.admin_client.post(
            "/api/warehouses/zones/",
            {
                "warehouse": wh.data["id"],
                "name": "InvCovZone",
                "temperature_zone": "ambient",
                "hazmat_class": "none",
            },
            format="json",
        )
        loc = self.admin_client.post(
            "/api/warehouses/locations/",
            {
                "zone": zone.data["id"],
                "code": "INVCOV-L1",
                "capacity_limit": "100.00",
                "capacity_unit": "units",
            },
            format="json",
        )

        plan = self.admin_client.post(
            "/api/inventory/plans/",
            {
                "title": "CoveragePlan",
                "region": "Mid",
                "asset_type": "Wheelchairs",
                "mode": "full",
            },
            format="json",
        )
        self.assertEqual(plan.status_code, 201)
        plan_id = plan.data["id"]

        task = self.admin_client.post(
            "/api/inventory/tasks/",
            {"plan": plan_id, "location": loc.data["id"]},
            format="json",
        )
        self.assertEqual(task.status_code, 201)
        task_id = task.data["id"]

        line = self.admin_client.post(
            "/api/inventory/lines/",
            {
                "task": task_id,
                "asset_code": "WC-COV",
                "book_quantity": "10.00",
                "physical_quantity": "8.00",
            },
            format="json",
        )
        self.assertEqual(line.status_code, 201)
        line_id = line.data["id"]

        tasks_list = self.admin_client.get("/api/inventory/tasks/")
        self.assertEqual(tasks_list.status_code, 200)
        self.assertTrue(any(t["id"] == task_id for t in tasks_list.data))

        lines_list = self.admin_client.get("/api/inventory/lines/")
        self.assertEqual(lines_list.status_code, 200)
        self.assertTrue(any(l["id"] == line_id for l in lines_list.data))

        plan_patch = self.admin_client.patch(
            f"/api/inventory/plans/{plan_id}/",
            {"title": "CoveragePlan Renamed"},
            format="json",
        )
        self.assertEqual(plan_patch.status_code, 200)
        self.assertEqual(plan_patch.data["title"], "CoveragePlan Renamed")

        task_patch = self.admin_client.patch(
            f"/api/inventory/tasks/{task_id}/",
            {"status": "in_progress"},
            format="json",
        )
        self.assertEqual(task_patch.status_code, 200)

        action = self.admin_client.post(
            f"/api/inventory/lines/{line_id}/corrective-action/",
            {
                "cause": "Counting error",
                "action": "Recount and relabel",
                "owner": self.admin_user.id,
                "due_date": "2026-04-01",
                "evidence": "photo",
            },
            format="json",
        )
        self.assertEqual(action.status_code, 201)

        ack = self.admin_client.post(
            f"/api/inventory/lines/{line_id}/acknowledge-action/",
            {},
            format="json",
        )
        self.assertEqual(ack.status_code, 200)
        self.assertTrue(ack.data["accountability_acknowledged"])
        refreshed = CorrectiveAction.objects.get(line_id=line_id)
        self.assertTrue(refreshed.accountability_acknowledged)

        # Delete ordering respects FK: delete line via model (no HTTP),
        # then task detail delete, then plan detail delete.
        InventoryCountLine.objects.filter(id=line_id).delete()
        self.assertEqual(
            self.admin_client.delete(
                f"/api/inventory/tasks/{task_id}/"
            ).status_code,
            204,
        )
        self.assertEqual(
            self.admin_client.delete(
                f"/api/inventory/plans/{plan_id}/"
            ).status_code,
            204,
        )
        self.assertEqual(
            self.admin_client.delete(
                f"/api/inventory/plans/{plan_id}/"
            ).status_code,
            404,
        )

    # --- Jobs: checkpoints upsert + failures list ---

    def test_job_checkpoint_upsert_and_failures_listing(self):
        job = Job.objects.create(
            organization=self.org,
            job_type="ingest.folder_scan",
            source_path="/tmp/coverage",
            payload_json={},
            trigger_type="manual",
            status=JobStatus.PENDING,
            priority=1,
            dedupe_key="coverage-ckpt",
        )

        cp_resp = self.admin_client.post(
            f"/api/jobs/{job.id}/checkpoints/",
            {
                "file_name": "rows.csv",
                "row_offset": 42,
                "attachment_index": 0,
                "state_json": {"stage": "parse"},
            },
            format="json",
        )
        self.assertEqual(cp_resp.status_code, 200)
        self.assertEqual(cp_resp.data["row_offset"], 42)
        self.assertEqual(
            JobCheckpoint.objects.filter(job=job, file_name="rows.csv").count(), 1
        )

        # Upsert (same file_name, new offset) should update in place
        cp_update = self.admin_client.post(
            f"/api/jobs/{job.id}/checkpoints/",
            {
                "file_name": "rows.csv",
                "row_offset": 99,
                "attachment_index": 2,
                "state_json": {"stage": "attach"},
            },
            format="json",
        )
        self.assertEqual(cp_update.status_code, 200)
        self.assertEqual(cp_update.data["row_offset"], 99)
        self.assertEqual(
            JobCheckpoint.objects.filter(job=job, file_name="rows.csv").count(), 1
        )

        JobFailure.objects.create(
            job=job,
            attempt=1,
            error_type="parse_error",
            error_message="Bad row 17",
        )
        failures_resp = self.admin_client.get(f"/api/jobs/{job.id}/failures/")
        self.assertEqual(failures_resp.status_code, 200)
        self.assertEqual(len(failures_resp.data), 1)
        self.assertEqual(failures_resp.data[0]["error_type"], "parse_error")

    # --- Trips: bookings/mine/ ---

    def test_my_bookings_returns_callers_own_bookings(self):
        trip = self.admin_client.post(
            "/api/trips/",
            {
                "title": "Mine Trip",
                "origin": "Origin",
                "destination": "Dest",
                "service_date": "2026-05-01",
                "pickup_window_start": "2026-05-01T08:00:00Z",
                "pickup_window_end": "2026-05-01T09:00:00Z",
                "timezone_id": "America/Chicago",
                "signup_deadline": "2026-05-01T05:30:00Z",
                "capacity_limit": 2,
                "pricing_model": "per_seat",
                "fare_cents": 1000,
                "tax_bps": 0,
                "fee_cents": 0,
            },
            format="json",
        )
        self.assertEqual(trip.status_code, 201)
        trip_id = trip.data["id"]

        book = self.senior_client.post(
            f"/api/trips/{trip_id}/bookings/", {"care_priority": 1}, format="json"
        )
        self.assertEqual(book.status_code, 201)

        mine = self.senior_client.get("/api/trips/bookings/mine/")
        self.assertEqual(mine.status_code, 200)
        self.assertEqual(len(mine.data), 1)
        self.assertEqual(mine.data[0]["id"], book.data["id"])

        other = self.admin_client.get("/api/trips/bookings/mine/")
        self.assertEqual(other.status_code, 200)
        self.assertEqual(other.data, [])
