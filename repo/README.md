# HarborOps Fullstack

Local Docker environment for the HarborOps Offline Logistics & Care Transit Suite.

## Quick Start

1. Start everything:

```bash
docker-compose up
```

The hyphenated legacy invocation and the modern `docker compose up` subcommand are both supported.

2. Manual security validation (same check also runs automatically at backend startup):

```bash
docker compose run --rm backend python manage.py check_security_config
```

Docker will build images automatically the first time.

Backend startup now fails fast on invalid security-critical settings: the entrypoint runs
`python manage.py check_security_config` before migrations and before serving traffic.

Equivalent helper script:

```bash
bash setup.sh
```

`docker-compose.yml` includes local-dev fallback secrets so `docker compose up` works without extra setup.
For stronger local security, generate and use a custom `.env` with `bash deploy/bootstrap_env.sh`.

## Encryption Key Setup and Rotation

`APP_AES256_KEY_B64` is required for startup and must be a unique base64-encoded 32-byte key.
Startup fails fast if the key is missing, placeholder-like, or the known insecure default.

Generate a key:

```bash
python3 -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
```

Rotation procedure:

1. Generate a new key and update `APP_AES256_KEY_B64` in your secret store or `.env`.
2. Validate config: `docker compose exec backend python manage.py check_security_config`.
3. Restart services that decrypt sensitive fields: `docker compose restart backend offline_ingest_worker`.
4. Confirm health: `curl -k https://localhost:8443/api/health/`.

Note: rotating this key without a data re-encryption plan can make previously encrypted values unreadable.

Runtime profile hardening:

- Secure defaults use `DJANGO_DEBUG=false`.
- `DJANGO_DEBUG=true` is rejected unless `APP_RUNTIME_PROFILE` is explicitly set to `dev`/`development`/`local`.

When running:

- HTTPS Gateway (frontend + API): `https://localhost:8443`
- MySQL: `localhost:3406`

## HTTPS on LAN

TLS terminates at the `proxy` service (Caddy) and forwards to frontend/backend containers.
Caddy now issues local certificates at runtime using `tls internal`; no private key/cert files are stored in git.
Certificate state persists in Docker volumes (`caddy_data`, `caddy_config`).

Verification checklist:

1. Start stack: `docker compose up -d --build`
2. Open `https://localhost:8443`
3. Verify API through TLS: `curl -k https://localhost:8443/api/health/`
4. Confirm secure cookies in browser devtools (`Secure` flag on session/csrf cookies)

Notes:

- Django HTTPS mode is enabled with `DJANGO_HTTPS_ENABLED=true`.
- Session and CSRF cookies are marked Secure in HTTPS mode.
- Trust Caddy's local CA if you want browser warning-free local HTTPS.

## Sensitive Files Policy

Never commit runtime-generated sensitive artifacts:

- TLS keys/certs (`deploy/certs/`)
- uploaded verification files (`backend/media/`)
- database backups (`backend/backups/`)

These paths are git-ignored on purpose.
If any were previously tracked, untrack once locally:

```bash
git rm -r --cached deploy/certs backend/media backend/backups
```

Recommended pre-commit/CI guardrail:

```bash
bash deploy/check_no_sensitive_runtime_artifacts.sh
```

Cleanup helper before packaging/release:

```bash
bash deploy/scrub_sensitive_runtime.sh
```

## Seeded Demo Users

Startup bootstraps a demo organization and users:

- Organization code: `HARBOR_DEMO`
- Org Admin: `orgadmin` / `SecurePass1234`
- Senior: `senior1` / `SecurePass1234`
- Family Member: `family1` / `SecurePass1234`
- Caregiver: `caregiver1` / `SecurePass1234`
- Platform Admin: `platform1` / `SecurePass1234`

Persona verification quick steps:

1. Run `docker compose up --build`.
2. Open `https://localhost:8443` and log in with each seeded user.
3. Confirm role entry points via `GET /api/access/me/roles/` and sidebar screens.

Auth and role APIs:

- `GET /api/auth/csrf/`
- `POST /api/auth/login/`
- `GET /api/access/me/roles/`
- `GET /api/trips/`

Core domain APIs:

- Trips: `/api/trips/*`
- Warehouses, zones, locations, partners: `/api/warehouses/*`
- Inventory plans/tasks/lines/variance closure: `/api/inventory/*`
- Offline jobs, dependencies, worker claim/heartbeat/checkpoints: `/api/jobs/*`
- Security unmasking and reveal flow: `/api/security/*`
- Monitoring anomaly alerts/thresholds: `/api/monitoring/*`

Self-service export APIs:

- `POST /api/auth/exports/request/` (creates `pending` request)
- `GET /api/auth/exports/` (list own requests)
- `GET /api/auth/exports/<id>/download/` (owner or `export.read.any`)

Request-signing scope:

- HMAC signing with timestamp/nonce replay prevention applies to mutating endpoints matching `REQUEST_SIGNING_PREFIXES` (default: `/api/`).
- Unauthenticated machine/API-key requests must include `X-Key-Id`, `X-Sign-Timestamp`, `X-Sign-Nonce`, and `X-Signature`.
- Authenticated browser/session mutations must include `X-Request-Timestamp`, `X-Request-Nonce`, and `X-Session-Signature` in addition to session auth, CSRF, and RBAC checks.
- Allowlisted unauthenticated auth routes bypass signing via `REQUEST_SIGNING_ALLOWLIST_PATHS` (default: `/api/auth/login/`, `/api/auth/register/`, `/api/auth/captcha/challenge/`).

Signing header contract:

- `X-Key-Id`: API client key id
- `X-Sign-Timestamp`: ISO-8601 UTC timestamp (max skew: 5 minutes)
- `X-Sign-Nonce`: unique request nonce (replay-blocked)
- `X-Signature`: hex HMAC-SHA256 over `METHOD\nPATH\nTIMESTAMP\nNONCE\nBODY`

Session signing header contract (authenticated browser mutations):

- `X-Request-Timestamp`: ISO-8601 UTC timestamp (max skew: 5 minutes)
- `X-Request-Nonce`: unique request nonce (single-use replay-blocked)
- `X-Session-Signature`: hex HMAC-SHA256 over `METHOD\nPATH\nTIMESTAMP\nNONCE` using the CSRF token (`X-CSRFToken` / `csrftoken`) as the per-session signing secret

Protected prefix defaults (`REQUEST_SIGNING_PREFIXES`):

- `/api/` (all mutating API routes except explicit allowlist paths)

Examples of protected mutation endpoints under this default include:

- `POST /api/jobs/`
- `POST /api/jobs/<id>/retry/`
- `POST /api/jobs/attachments/dedupe-check/`
- `POST /api/monitoring/thresholds/`
- `POST /api/trips/bookings/<id>/cancel/`

Trip waypoint PATCH semantics (`PATCH /api/trips/<id>/`):

- Including `waypoints` replaces the full waypoint list atomically.
- `sequence` values must be unique contiguous integers starting at `1`; invalid sequences return `400`.
- Material waypoint changes create a new trip version snapshot and require rider re-acknowledgment.

Booking timeline access policy (`GET /api/trips/bookings/<id>/timeline/`):

- Owner rider can view timeline.
- Operations roles (`trip.write`, including caregiver and org admin defaults) can view timeline.
- Non-owner rider/family users are denied (`403`).

Operational commands (run in backend container):

```bash
docker compose exec backend python manage.py backup_db
docker compose exec backend python manage.py restore_db_drill
docker compose exec backend python manage.py restore_db_drill --execute
docker compose exec backend python manage.py restore_db_drill --execute --admin-user root --admin-password "$MYSQL_ROOT_PASSWORD"
docker compose exec backend python manage.py detect_anomalies
docker compose exec backend python manage.py check_security_config
docker compose exec backend python manage.py process_exports
```

`restore_db_drill --execute` requires DB credentials with create/drop privileges for temporary drill databases.
By default, execute mode uses `DB_ADMIN_USER` / `DB_ADMIN_PASSWORD` (falls back to `DB_USER` / `DB_PASSWORD`).

## Nightly Backups

`backup_scheduler` runs `backup_db` automatically every night (default 02:00, local container time).
When backup execution fails, the scheduler exits so the failure is visible and can be restarted/alerted externally.

Configuration env vars:

- `BACKUP_SCHEDULE_HOUR` (default `2`)
- `BACKUP_SCHEDULE_MINUTE` (default `0`)
- `BACKUP_RETENTION_DAYS` (default `30`)

`BACKUP_PASSPHRASE` must be explicitly set to a strong non-default value (minimum 12 chars). `backup_db` fails fast when passphrase is empty or uses default placeholders.

Retention verification:

```bash
docker compose exec backend python manage.py backup_db
docker compose exec backend ls /app/backups
```

Old encrypted backups beyond retention are removed on each run.

Recovery drill procedure:

```bash
docker compose exec backend python manage.py restore_db_drill
docker compose exec backend python manage.py restore_db_drill --execute
```

Execute mode imports into a temporary database and drops it after validation.

## Structured Logging Taxonomy

Application logs now emit structured JSON records with explicit categories via `harborops.<category>` loggers.

Current category taxonomy:

- `audit`
- `auth`
- `trips`
- `jobs`
- `inventory`
- `warehouse`
- `verification`
- `security`
- `monitoring`
- `system`

Each record includes `timestamp`, `level`, `logger`, `message`, and an `event` payload with category/action metadata.

## Inventory Variance Rules

Variance categories:

- `missing`: physical quantity < book quantity
- `extra`: physical quantity > book quantity
- `data_mismatch`: identifier/location mismatch (`attribute_mismatch=true`, mismatched `observed_asset_code`, or mismatched `observed_location_code`)

`data_mismatch` always routes to review (`requires_review=true`) even when quantity variance is zero.

## Frontend Integration Tests

Run the React test suite and production build inside the frontend Docker container. The full stack (`db`, `backend`, `proxy`) must be up first because the integration tests make real HTTPS calls — no fetch mocks, no canned responses.

```bash
docker compose up -d --build
docker compose run --rm frontend npm run lint
docker compose run --rm frontend npm run test:run
docker compose run --rm frontend npm run build
```

Test composition:

- `src/hooks/domains/*.test.js` — pure domain/reducer unit tests.
- `src/screens/*.test.jsx` — prop-driven React Testing Library render tests.
- `src/realBackend.integration.test.js` — real-network integration suite. Every request is an actual HTTPS call through the Caddy proxy (`https://proxy:8443`) to the live Django backend: CSRF issuance, login/me/roles, trips RBAC, signed favorite create+delete round-trip, and unsigned-mutation rejection by the session signing middleware.

All frontend tooling runs inside the Docker image; no local Node.js install is required.

Worker endpoints under `/api/jobs/worker/*` require HMAC request signing headers:

- `X-Key-Id`
- `X-Sign-Timestamp` (ISO8601, 5-minute validity)
- `X-Sign-Nonce` (single-use)
- `X-Signature` (hex HMAC-SHA256 over method/path/timestamp/nonce/body)

Worker heartbeat mismatch (`/api/jobs/worker/<id>/heartbeat/`) returns a controlled `409` JSON response with `code=lease_owner_mismatch` when lease owner does not match `worker_id`.
Worker complete/fail endpoints also require `worker_id` and enforce lease-owner checks with the same controlled `409` mismatch response.

Monitoring thresholds write policy:

- `GET /api/monitoring/thresholds/` requires `monitoring.read`.
- `POST /api/monitoring/thresholds/` requires `monitoring.write`.

## Runtime Verification (Docker)

Use the reproducible verifier script:

```bash
bash deploy/verify_runtime.sh
```

The script captures command output and endpoint responses into `.tmp/runtime_verification/<timestamp>/`.
For the full audit checklist (including manual UI screenshot evidence for role workspaces), see `deploy/runtime_verification_checklist.md`.

## End-to-End Test Runner (Docker)

Run the complete backend + frontend test flow in Docker:

```bash
bash run_tests.sh
```

`run_tests.sh` resets the Docker stack, starts services, waits for health, runs backend `tests` (all modules), then runs frontend `test:run` and `build`.
Backend startup in that flow also runs `python manage.py check_security_config` before migrations and before serving traffic.
It enforces sensitive-artifact guardrails, runs a non-mocked frontend-backend smoke flow (frontend shell load + real login + role check + write action), and scrubs sensitive runtime artifacts at the end.

CI now also runs this real smoke path on push/PR via `.github/workflows/real-frontend-backend-smoke.yml`.

For local frontend-only verification with archived logs:

```bash
bash deploy/verify_frontend_local.sh
```

Logs are written to `.tmp/frontend_verification/<timestamp>/`.

## Offline Folder Ingest Worker

`offline_ingest_worker` scans configured local drop folders for CSV and image files.

- Manual trigger: create a job with `job_type=ingest.folder_scan` and `source_path`.
- Scheduled trigger: worker auto-enqueues scheduled scans when `OFFLINE_INGEST_FOLDERS` is set.
- Resume behavior: row and attachment checkpoints are persisted in `JobCheckpoint`, so retries resume from the last processed offset.

Run once manually in backend container:

```bash
docker compose exec backend python manage.py run_offline_ingest_worker --once --schedule
```

Demo resumable failure/retry flow:

```bash
docker compose exec backend python manage.py run_offline_ingest_worker --once --simulate-failure-after-rows 1
docker compose exec backend python manage.py run_offline_ingest_worker --once
```

## Verification Upload Workflow

Verification requests support concrete document upload intake:

- Upload: `POST /api/auth/verification-requests/<id>/documents/upload/` (multipart)
- Open/review: `GET /api/auth/verification-documents/<id>/open/` (owner or verification reviewer)

Supported MIME types: `image/jpeg`, `image/png`, `application/pdf`, max 10 MB.

## Sensitive Traveler Fields

Traveler profiles store encrypted-at-rest values for identifier, government ID, and credential number.

- Default profile API responses are masked.
- Unmask requires `sensitive.unmask` permission, explicit reason, and active unmask session.
- Reveal endpoints are audited and field-scoped:
  - `/api/security/traveler-profiles/<id>/reveal/`
  - `/api/security/traveler-profiles/<id>/reveal/government-id/`
  - `/api/security/traveler-profiles/<id>/reveal/credential-number/`

To stop:

```bash
docker compose down
```

To reset database volume:

```bash
docker compose down -v
```
