# HarborOps Design

## Overview

HarborOps is a multi-tenant logistics and care-transit platform with role-based access control, auditable workflows, and secure handling for sensitive data.

Runtime topology (local Docker):

- `proxy` (Caddy): TLS termination and routing at `https://localhost:8443`
- `frontend` (Vite React app): UI service behind proxy
- `backend` (Django + DRF): API, authz, business workflows
- `db` (MySQL): primary persistence
- `offline_ingest_worker`: scheduled/offline job processing loop
- `backup_scheduler`: nightly encrypted backup runner

## Design Goals

- Enforce strict tenant and object-level isolation.
- Keep mutating operations explicitly permission-gated.
- Support both interactive browser sessions and machine-signed worker traffic.
- Preserve a strong audit trail for sensitive actions.
- Keep local runtime reproducible with a single Docker command.

## Backend Architecture

Domain apps:

- `accounts`: users, preferences, traveler profiles, verification, exports
- `access`: roles and permission introspection
- `trips`: trip lifecycle, booking lifecycle, fare/timeline/versioning
- `warehouse`: warehouses, zones, locations, partner records
- `inventory`: plans/tasks/count lines/variance corrective actions
- `jobs`: background jobs, worker lease flow, dedupe/checkpoints/errors
- `security`: unmask session and sensitive field reveal workflows
- `monitoring`: anomaly alerts and threshold configuration
- `audit`: structured audit events
- `core`: shared middleware, security config, health, utilities

Request path composition:

- root: `backend/harborops_backend/urls.py`
- API aggregation: `backend/core/urls.py`
- app-local routers in each `<app>/urls.py`

## Security Model

### Authn/Authz

- Browser/API user traffic uses session authentication and CSRF.
- Machine/worker traffic under configured signing prefixes uses HMAC signing.
- RBAC is permission-based (for example `trip.write`, `booking.write`, `monitoring.write`) and supplemented with organization/object scope checks.

### Tenant Isolation

- Every core model operation is constrained to active organization context.
- Cross-tenant reads and mutations are denied with explicit `403`/`404` paths.
- Sensitive document/open/reveal/export download routes also enforce tenant ownership rules.

### Sensitive Data Handling

- High-risk profile fields are encrypted with AES-256-GCM (`APP_AES256_KEY_B64`).
- Unmasking is session-based and auditable; reveal actions are separately permissioned.
- Export flows support masked/unmasked controls and justification requirements.

### Auditing and Observability

- Structured logs with explicit category/action metadata.
- Audit records capture actor, organization, resource, and relevant metadata.
- Key security and workflow operations emit deterministic events.

## Core Workflow Designs

### Trip + Booking Lifecycle

- Trips can be drafted, published/unpublished, and versioned.
- Waypoint patch semantics use full replacement with sequence validation.
- Material trip updates can force rider re-acknowledgment.
- Booking cancellation/refund/no-show flows require appropriate role permissions and scope.

### Jobs + Worker Lease Model

- Worker claims establish lease ownership.
- Heartbeat/complete/fail enforce lease-owner consistency.
- Mismatches return controlled `409` conflict responses.
- Replay-resistant signing protects worker and configured job mutation routes.

### Verification + Export Lifecycle

- Verification requests support review and document upload/open flows.
- Data exports are asynchronous (`pending -> ready/failed`) via `process_exports`.
- Export downloads are owner-restricted unless elevated permission (`export.read.any`) exists.

### Inventory Variance Resolution

- Variances classify into `missing`, `extra`, `data_mismatch`.
- Corrective action create/approve/acknowledge/close flow tracks accountability.
- `data_mismatch` always routes to review paths even with zero quantity delta.

## Data + Runtime Operations

### Persistence and Backup

- MySQL is the source of truth for transactional data.
- `backup_scheduler` runs encrypted dumps with retention cleanup.
- `restore_db_drill` provides dry-run and execute drill modes.

### Local Runtime Defaults

- `docker-compose.yml` includes local defaults so `docker compose up` works from scratch.
- Optional `.env` values override compose defaults when present.
- Public host exposure is limited to TLS gateway (`8443`) and MySQL (`3406`).

## Testing Strategy

- Backend E2E/security suite validates auth, RBAC, tenant isolation, and critical lifecycle paths.
- Frontend integration tests cover core workspace navigation and jobs UX flows.
- `run_tests.sh` executes full Docker-based backend + frontend verification path.

## Tradeoffs

- Local compose defaults prioritize developer startup simplicity over secret hygiene for production contexts.
- Session auth + request signing split adds complexity but cleanly supports user and worker trust models.
- Strict conflict and denial responses improve auditability and deterministic client behavior.
