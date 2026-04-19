# Runtime Verification Checklist

Use this checklist for audit evidence collection against the Docker runtime.

## Prerequisites

- `APP_AES256_KEY_B64` exported in shell (unique base64-encoded 32-byte key).
- Docker running locally.

## Automated verification run

1. Run `bash deploy/verify_runtime.sh`.
   - Note: this script performs `docker compose down -v` first to ensure a clean, reproducible startup.
2. Save the generated artifact folder path from script output.
3. Confirm these files exist in the artifact folder:
   - `docker_up.log`
   - `health.json`
   - `security_config_check.txt`
   - `login.json`
   - `roles.json`
   - `trips.json`
   - `jobs.json`
   - `worker_orchestration_tests.txt`

## Manual UI evidence (screenshots)

Capture screenshots from `https://localhost:8443` after login with seeded users:

1. Org admin dashboard/workspace showing trips + jobs access.
2. Senior workspace showing rider-level view and no operations-only controls.
3. Verification/review screen with high-risk request requiring distinct reviewers.

Store screenshots in the same artifact folder under `screenshots/`.

## Expected assertions

- Startup succeeds only when `APP_AES256_KEY_B64` is valid.
- Login succeeds for seeded org admin.
- Roles endpoint returns expected org-admin role mapping.
- Trips/jobs endpoints return authenticated data.
- Worker orchestration tests pass for:
  - per-org concurrency limit enforcement,
  - dependency blocking until prerequisite success,
  - lease-owner enforcement on heartbeat/complete/fail worker endpoints.
- Request-signing controls are validated for worker routes (`/api/jobs/worker/*`) with replay protection in place.

## Optional teardown

- `docker compose down`
