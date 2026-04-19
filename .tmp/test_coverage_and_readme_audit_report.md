# Test Coverage Audit

## Scope, Mode, and Project Type
- Audit mode: static inspection only (no execution).
- Recheck timestamp: 2026-04-19.
- Project type: `fullstack` (explicitly declared in `README.md:1`).
- Backend routing source: `backend/harborops_backend/urls.py` -> `backend/core/urls.py` -> app URL modules.

## Backend Endpoint Inventory
Total unique backend endpoints (METHOD + resolved PATH): **97**.

Coverage state after your update:
- Covered by backend HTTP tests: **96**
- Not covered: **1**
- Only endpoint still not directly exercised: `GET /api/jobs/<int:job_id>/row-errors/`

Evidence for newly-covered endpoints from your update file:
- `GET /api/health/`: `backend/tests/test_endpoint_coverage_completion.py:76`
- `GET /api/access/me/roles/`: `backend/tests/test_endpoint_coverage_completion.py:81`
- `POST /api/auth/change-password/`: `backend/tests/test_endpoint_coverage_completion.py:90`
- `GET/PUT /api/auth/preferences/`: `backend/tests/test_endpoint_coverage_completion.py:102,106`
- `GET/PUT traveler profile routes`: `backend/tests/test_endpoint_coverage_completion.py:136,141`
- `POST /api/auth/deletion-request/`: `backend/tests/test_endpoint_coverage_completion.py:167`
- `GET /api/auth/exports/`: `backend/tests/test_endpoint_coverage_completion.py:186`
- Warehouse CRUD detail/list coverage (`GET/PUT/DELETE` on zone/location/partner/warehouse): `backend/tests/test_endpoint_coverage_completion.py:240-308`
- Inventory detail/list/ack coverage (`GET /tasks`, `GET /lines`, `PATCH/DELETE detail`, `POST acknowledge-action`): `backend/tests/test_endpoint_coverage_completion.py:372-435`
- Jobs checkpoints and failures routes: `backend/tests/test_endpoint_coverage_completion.py:455-493`
- `GET /api/trips/bookings/mine/`: `backend/tests/test_endpoint_coverage_completion.py:528`

## API Test Mapping Table

### Uncovered Endpoint(s)
| Endpoint | Covered | Test Type | Test File(s) | Evidence |
|---|---|---|---|---|
| `GET /api/jobs/<int:job_id>/row-errors/` | No | unit-only / indirect | - | no direct `APIClient().get("/api/jobs/{id}/row-errors/")` found in backend tests |

### Covered Endpoint Families (all listed routes in each family have direct HTTP coverage)
| Family | Covered Methods/Paths | Test Type | Evidence |
|---|---|---|---|
| core | `/api/health/` | true no-mock HTTP | `test_endpoint_coverage_completion.py:76` |
| access | `/api/access/me/roles/` | true no-mock HTTP | `test_endpoint_coverage_completion.py:81` |
| accounts auth/profile/export | csrf/register/login/logout/me/change-password/captcha/preferences/traveler profiles/exports/deletion/verification docs+reviews | true no-mock HTTP | `test_e2e_suite.py`, `test_security_controls.py`, `test_endpoint_coverage_completion.py` |
| trips | trip list/create/patch/publish/unpublish/versions/bookings/fare-estimate/mine/booking actions+timeline | true no-mock HTTP | `test_e2e_suite.py`, `test_security_controls.py`, `test_endpoint_coverage_completion.py:502-533` |
| warehouses | list/create + detail PUT/DELETE + zone/location/partner list/create/detail PUT/DELETE | true no-mock HTTP | `test_e2e_suite.py`, `test_endpoint_coverage_completion.py:195-308` |
| inventory | plans/tasks/lines list/create + plan/task PATCH/DELETE + corrective/approve/ack/close routes | true no-mock HTTP | `test_e2e_suite.py`, `test_endpoint_coverage_completion.py:339-435` |
| jobs | `/api/jobs/`, retry, checkpoints, failures, row-error-resolve, dedupe-check, worker claim/heartbeat/complete/fail | true no-mock HTTP (except one mixed case) | `test_e2e_suite.py`, `test_security_controls.py`, `test_endpoint_coverage_completion.py:455-493` |
| monitoring | alerts list/ack + thresholds get/post | true no-mock HTTP | `test_e2e_suite.py`, `test_security_controls.py` |
| security | unmask session + traveler reveal endpoints | true no-mock HTTP | `test_e2e_suite.py` |

## API Test Classification
1. True no-mock HTTP
- Primary files: `backend/tests/test_e2e_suite.py`, `backend/tests/test_security_controls.py`, `backend/tests/test_endpoint_coverage_completion.py`.

2. HTTP with mocking
- `POST /api/jobs/` has one mocked-path test:
  - `backend/tests/test_security_controls.py:354` patches `jobs.views.validate_dependency_graph` during request handling.
- Note: the same endpoint also has no-mock coverage elsewhere.

3. Non-HTTP tests
- `backend/tests/test_restore_db_drill.py` (management command + patched subprocess).
- command/security checks in `test_e2e_suite.py` (e.g., patched backup command execution path).

## Mock Detection
Backend:
- `backend/tests/test_security_controls.py:354` -> `patch("jobs.views.validate_dependency_graph", ...)`
- `backend/tests/test_restore_db_drill.py:39,69` -> patched `subprocess.run`
- `backend/tests/test_e2e_suite.py:2438` -> patched `core.management.commands.backup_db.subprocess.run`

Frontend:
- No frontend transport-layer mocking detected in current frontend test files (`*.test.*`, `*.spec.*`).
- Real no-mock frontend integration coverage present in:
  - `repo/frontend/src/realBackend.integration.test.js` (live HTTPS requests through Caddy proxy to Django backend, explicit "no fetch mocks" contract in file header/comments and request implementation).

## Coverage Summary
- Total endpoints: **97**
- Endpoints with HTTP tests: **96**
- Endpoints with true no-mock HTTP coverage: **96**

Computed:
- HTTP coverage %: **98.97%**
- True API coverage %: **98.97%**

## Unit Test Summary

### Backend Unit/Integration Tests
Test files:
- `backend/tests/test_e2e_suite.py`
- `backend/tests/test_security_controls.py`
- `backend/tests/test_restore_db_drill.py`
- `backend/tests/test_endpoint_coverage_completion.py`

Covered backend modules:
- controllers/views: accounts, access, trips, warehouse, inventory, jobs, monitoring, security, core
- auth/security controls: signing/replay/CSRF/RBAC/object auth
- command-layer: restore drill, backup/security config checks

Important backend module gap still present:
- Jobs row error list endpoint path not directly hit:
  - `GET /api/jobs/<int:job_id>/row-errors/`

### Frontend Unit Tests (STRICT REQUIREMENT)
Frontend unit tests detected with direct file evidence:
- `frontend/src/screens/ProfileScreen.test.jsx`
- `frontend/src/screens/JobsScreen.test.jsx`
- `frontend/src/screens/InventoryScreen.test.jsx`
- `frontend/src/hooks/domains/profileDomain.test.js`
- `frontend/src/hooks/domains/inventoryDomain.test.js`
- `frontend/src/hooks/domains/tripsDomain.test.js`

Framework/tools:
- Vitest + React Testing Library + jest-dom
- Evidence: `frontend/package.json`, `frontend/src/test/setup.js`

Covered frontend modules/components:
- `ProfileScreen`, `JobsScreen`, `InventoryScreen`, and domain modules (`profileDomain`, `inventoryDomain`, `tripsDomain`)

Important frontend modules still lacking direct unit tests:
- `WarehouseScreen.jsx`, `TripsScreen.jsx`, `VerificationScreen.jsx`
- controller hooks (`useTripsController`, `useJobsController`, `useOperationsController`, etc.)

**Frontend unit tests: PRESENT**

Cross-layer observation:
- Backend coverage is now near-complete.
- Frontend has both unit tests and real no-mock backend integration tests.

## API Observability Check
- Strong overall.
- Most tests show explicit method+path, concrete payloads, and response assertions.
- Weakness concentrated in the single uncovered endpoint (no request/response observability).

## Tests Check
- `run_tests.sh` remains Docker-based end-to-end runner: `repo/run_tests.sh`.
- Includes backend tests, frontend tests/build, and smoke flow: static check result = **OK**.

## Test Coverage Score (0–100)
**96/100**

## Score Rationale
- Large increase from prior audit due targeted no-mock HTTP additions in `test_endpoint_coverage_completion.py`.
- Near-complete endpoint coverage (96/97).
- Minor deductions:
  - one uncovered endpoint (`GET /api/jobs/<id>/row-errors/`)
  - one mocked API path case (`POST /api/jobs/` in a specific test)


## Key Gaps
- Add one direct backend HTTP test for `GET /api/jobs/<int:job_id>/row-errors/`.
- Optional: add direct unit coverage for major frontend controller hooks/screens not currently unit-tested.

## Confidence & Assumptions
- Confidence: high.
- Assumptions:
  - Endpoint method set inferred from `APIView` methods (`get/post/put/patch/delete`).
  - Coverage counted only when backend tests directly issue matching METHOD+PATH requests.

---

# README Audit

## README Location
- Present: `repo/README.md`

## Hard Gate Evaluation

### Formatting
- PASS

### Startup Instructions (Backend/Fullstack)
- PASS: includes required literal `docker-compose up` (`README.md:10`).

### Access Method
- PASS: explicit URL/port and access path (`README.md:62,74,125`).

### Verification Method
- PASS: concrete verification steps including curl checks (`README.md:51,75`).

### Environment Rules (Docker-contained)
- PASS: frontend test/build instructions moved to Docker execution (`README.md:274-276`).
- No local `npm install`/`npm ci` requirement in README.

### Demo Credentials (auth exists)
- PASS: credentials listed for all roles (`README.md:116-120`).

## Engineering Quality
- Tech stack clarity: strong
- Architecture/workflow explanation: strong operational detail
- Testing instructions: strong (`README.md:314`, plus runtime verification sections)
- Security/roles documentation: strong

## High Priority Issues
- None.

## Medium Priority Issues
- None blocking; optional consolidation of very long operational sections.

## Low Priority Issues
- README is dense; a short “minimum happy path” block could improve scan speed.

## Hard Gate Failures
- None.

## README Verdict
**PASS**

## Final Verdicts
- Test Coverage Audit: **PASS (with minor residual gap)**
- README Audit: **PASS**


