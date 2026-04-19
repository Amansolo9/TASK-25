# HarborOps API Spec

Base URL (local): `https://localhost:8443`

- All API routes are under `/api/`.
- Session-authenticated endpoints use CSRF protection.
- Machine-to-machine job routes use HMAC request signing (see Request Signing).

## Authentication

### Session + CSRF

- `GET /api/auth/csrf/` - Issue CSRF cookie/token.
- `POST /api/auth/register/` - Register user.
- `POST /api/auth/login/` - Login with credentials.
- `POST /api/auth/logout/` - Logout current session.
- `GET /api/auth/me/` - Get current user profile/session context.
- `POST /api/auth/change-password/` - Change password.
- `GET /api/access/me/roles/` - Get effective roles/permissions.

### CAPTCHA

- `GET /api/auth/captcha/challenge/` - Create/refresh challenge for guarded login flows.

## Accounts and User Data

- `GET /api/auth/preferences/` - Get preferences.
- `PATCH /api/auth/preferences/` - Update preferences.

Traveler profiles:

- `GET /api/auth/traveler-profiles/`
- `POST /api/auth/traveler-profiles/`
- `GET /api/auth/traveler-profiles/{profile_id}/`
- `PATCH /api/auth/traveler-profiles/{profile_id}/`
- `DELETE /api/auth/traveler-profiles/{profile_id}/`

Local alerts:

- `GET /api/auth/alerts/`
- `POST /api/auth/alerts/{alert_id}/acknowledge/`

Favorites / comparisons:

- `GET /api/auth/favorites/`
- `POST /api/auth/favorites/`
- `DELETE /api/auth/favorites/{favorite_id}/`
- `GET /api/auth/comparisons/`
- `POST /api/auth/comparisons/`
- `DELETE /api/auth/comparisons/{comparison_id}/`

Account deletion:

- `POST /api/auth/deletion-request/`

## Verification

- `GET /api/auth/verification-requests/`
- `POST /api/auth/verification-requests/`
- `POST /api/auth/verification-requests/{verification_id}/review/`
- `POST /api/auth/verification-requests/{verification_id}/documents/upload/`
- `GET /api/auth/verification-documents/{document_id}/open/`

## Self-Service Exports

- `GET /api/auth/exports/` - List caller export requests.
- `POST /api/auth/exports/request/` - Create export request (starts `pending`).
- `GET /api/auth/exports/{export_id}/download/` - Download when `ready`.

Export lifecycle:

- `pending` -> `ready` or `failed`.
- Exports are processed by management command: `python manage.py process_exports`.

## Trips and Bookings

Trips:

- `GET /api/trips/`
- `POST /api/trips/`
- `GET /api/trips/{trip_id}/`
- `PATCH /api/trips/{trip_id}/`
- `POST /api/trips/{trip_id}/publish/`
- `POST /api/trips/{trip_id}/unpublish/`
- `GET /api/trips/{trip_id}/versions/`
- `GET /api/trips/{trip_id}/fare-estimate/`

Bookings:

- `POST /api/trips/{trip_id}/bookings/`
- `GET /api/trips/bookings/mine/`
- `POST /api/trips/bookings/{booking_id}/ack/`
- `POST /api/trips/bookings/{booking_id}/cancel/`
- `POST /api/trips/bookings/{booking_id}/no-show/`
- `POST /api/trips/bookings/{booking_id}/refund-request/`
- `POST /api/trips/bookings/{booking_id}/refund-decision/`
- `GET /api/trips/bookings/{booking_id}/timeline/`

## Warehouses

- `GET /api/warehouses/`
- `POST /api/warehouses/`
- `GET /api/warehouses/{warehouse_id}/`
- `PATCH /api/warehouses/{warehouse_id}/`
- `DELETE /api/warehouses/{warehouse_id}/`

Zones:

- `GET /api/warehouses/zones/`
- `POST /api/warehouses/zones/`
- `GET /api/warehouses/zones/{zone_id}/`
- `PATCH /api/warehouses/zones/{zone_id}/`
- `DELETE /api/warehouses/zones/{zone_id}/`

Locations:

- `GET /api/warehouses/locations/`
- `POST /api/warehouses/locations/`
- `GET /api/warehouses/locations/{location_id}/`
- `PATCH /api/warehouses/locations/{location_id}/`
- `DELETE /api/warehouses/locations/{location_id}/`

Partners:

- `GET /api/warehouses/partners/`
- `POST /api/warehouses/partners/`
- `GET /api/warehouses/partners/{partner_id}/`
- `PATCH /api/warehouses/partners/{partner_id}/`
- `DELETE /api/warehouses/partners/{partner_id}/`

## Inventory

- `GET /api/inventory/plans/`
- `POST /api/inventory/plans/`
- `GET /api/inventory/plans/{plan_id}/`
- `PATCH /api/inventory/plans/{plan_id}/`

- `GET /api/inventory/tasks/`
- `POST /api/inventory/tasks/`
- `GET /api/inventory/tasks/{task_id}/`
- `PATCH /api/inventory/tasks/{task_id}/`

- `POST /api/inventory/lines/`
- `POST /api/inventory/lines/{line_id}/corrective-action/`
- `POST /api/inventory/lines/{line_id}/approve-action/`
- `POST /api/inventory/lines/{line_id}/acknowledge-action/`
- `POST /api/inventory/lines/{line_id}/close/`

## Jobs

General jobs:

- `GET /api/jobs/`
- `POST /api/jobs/`
- `POST /api/jobs/{job_id}/retry/`
- `POST /api/jobs/{job_id}/checkpoints/`
- `GET /api/jobs/{job_id}/failures/`
- `GET /api/jobs/{job_id}/row-errors/`
- `POST /api/jobs/row-errors/{error_id}/resolve/`
- `POST /api/jobs/attachments/dedupe-check/`

Worker routes:

- `POST /api/jobs/worker/claim/`
- `POST /api/jobs/worker/{job_id}/heartbeat/`
- `POST /api/jobs/worker/{job_id}/complete/`
- `POST /api/jobs/worker/{job_id}/fail/`

## Monitoring

- `GET /api/monitoring/alerts/`
- `POST /api/monitoring/alerts/{alert_id}/ack/`
- `GET /api/monitoring/thresholds/`
- `POST /api/monitoring/thresholds/`

## Security / Unmasking

- `POST /api/security/unmask-sessions/`
- `POST /api/security/traveler-profiles/{profile_id}/reveal/`
- `POST /api/security/traveler-profiles/{profile_id}/reveal/{sensitive_field}/`

## Health

- `GET /api/health/`

## Request Signing (HMAC)

Default protected prefix: `/api/jobs/`.

Required headers:

- `X-Key-Id`
- `X-Sign-Timestamp` (ISO8601 UTC, +/- 5 minute skew)
- `X-Sign-Nonce` (single use per key)
- `X-Signature` (hex HMAC-SHA256 over `METHOD\nPATH\nTIMESTAMP\nNONCE\nBODY`)

Common signing error response codes:

- `signing_headers_missing`
- `signing_timestamp_invalid`
- `signing_timestamp_expired`
- `signing_key_invalid`
- `signing_key_material_unavailable`
- `signing_signature_mismatch`
- `signing_nonce_replay`

## Common Status Patterns

- `200` / `201` successful operations.
- `400` request validation failures.
- `401` authentication or signing failures.
- `403` permission/tenant/object-scope denials.
- `404` object not found within caller scope.
- `409` conflict (for example lease-owner mismatch or already-reviewed verification).
