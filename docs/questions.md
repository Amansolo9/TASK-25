# HarborOps Prompt Clarification Questions

This document captures each ambiguity as:
- **Question**: what needs stakeholder confirmation
- **My Understanding**: current interpretation for implementation
- **Solution**: proposed requirement refinement

## 1) Offline Scope
**Question**  
Does "without relying on the internet" mean fully air-gapped operations, or just no cloud/runtime dependency?

**My Understanding**  
The platform must continue to function with zero internet connectivity during normal operations.

**Solution**  
Define deployment as **internet-independent**: all core features work offline; internet is optional only for patch/update procedures.

## 2) Deployment Topology
**Question**  
Is this a single-organization install per site, or a multi-tenant on-prem installation serving many organizations?

**My Understanding**  
Likely multi-organization support is required due to org-level concurrency and role boundaries.

**Solution**  
Specify **single shared on-prem cluster with strict tenant isolation** by `organization_id` across all API and DB queries.

## 3) Authentication Model
**Question**  
Is login strictly username/password, or should privileged users also require local MFA?

**My Understanding**  
Baseline requirement is username/password only.

**Solution**  
Keep password auth mandatory for all; add **optional local TOTP MFA** for Org Admin and Platform Admin in v1.1.

## 4) Password Policy Details
**Question**  
Are there additional password controls (history, expiry, reset constraints) beyond length and character composition?

**My Understanding**  
Only minimum rule is currently specified.

**Solution**  
Define: min 12 chars, at least one letter and one number, disallow last 5 passwords, no forced expiry unless compromised.

## 5) Role Model Granularity
**Question**  
Are roles fixed or configurable with custom permissions?

**My Understanding**  
Core roles are fixed but screen-level authorization is required.

**Solution**  
Implement **fixed base roles + permission matrix** (feature/screen/action), with Org Admin assignable subsets.

## 6) Platform Admin Scope
**Question**  
Can Platform Admin access all tenant data including unmasked sensitive fields?

**My Understanding**  
Platform Admin needs operational oversight but should still follow least privilege.

**Solution**  
Allow cross-org metadata/admin functions; sensitive unmasking requires explicit justification and is fully audited.

## 7) Verification Workflow Ownership
**Question**  
Which roles can approve identity/credential verification, and is dual approval required?

**My Understanding**  
"Approved staff" implies delegated reviewers.

**Solution**  
Define `Verifier` permission (Caregiver Senior, Org Admin). For high-risk credentials, require dual approval; else single approval.

## 8) Upload File Constraints
**Question**  
What file formats, size limits, and resolution requirements apply to uploaded IDs/credentials?

**My Understanding**  
Image upload is required but limits are unspecified.

**Solution**  
Allow JPG/PNG/PDF, max 10 MB per file, minimum 1200 px long edge for images.

## 9) OCR vs Manual Review
**Question**  
Should verification include OCR extraction or manual review only?

**My Understanding**  
Offline environment favors manual review first.

**Solution**  
Use manual review in v1; OCR optional plug-in later, disabled by default.

## 10) PII Masking Standards
**Question**  
Which fields are masked by default and what masking format should each use?

**My Understanding**  
Government ID, credential numbers, traveler identifiers must be masked unless privileged access is justified.

**Solution**  
Define per-field mask policy (e.g., show last 4 only) in a central masking service shared by API/UI.

## 11) Unmask Access Control
**Question**  
What is required to view unmasked values (reason text, approval, timeout)?

**My Understanding**  
Unmasking should be rare, role-gated, and auditable.

**Solution**  
Require reason entry, role permission check, 10-minute temporary reveal token, and immutable audit record.

## 12) Trip Versioning Triggers
**Question**  
Which trip changes require re-acknowledgment from already signed-up riders?

**My Understanding**  
Material changes should trigger a new version and rider re-ack.

**Solution**  
Trigger re-ack when route, time window, date, fare rules, capacity, or deadline changes.

## 13) Capacity Reduction Policy
**Question**  
If capacity is lowered below current signups, how are impacted riders chosen?

**My Understanding**  
A deterministic policy is needed to avoid disputes.

**Solution**  
Apply priority: medical priority > existing confirmed order by signup timestamp > waitlist migration with notice.

## 14) Booking Lifecycle Rules
**Question**  
What are cancellation windows, waitlist behavior, no-show rules, and refund handling?

**My Understanding**  
Lifecycle must be explicit for operational consistency.

**Solution**  
Define statuses (`draft`, `live`, `booked`, `waitlisted`, `cancelled`, `completed`, `no_show`) and rules per transition.

## 15) Pricing Precision
**Question**  
How should USD rounding, tax, and fees be handled?

**My Understanding**  
Flat fare/per-seat is required, tax behavior unspecified.

**Solution**  
Store monetary values in cents, round half-up to 2 decimals, taxes/fees configurable per organization.

## 16) Time Zone and DST
**Question**  
Are all trip times local site time, and how should DST edge cases be resolved?

**My Understanding**  
Regional operations imply local-time scheduling.

**Solution**  
Persist UTC + timezone ID; render in org-local time; validate DST ambiguous/nonexistent times at save.

## 17) Warehouse Hierarchy Constraints
**Question**  
Can a location belong to multiple zones, and what unit defines capacity?

**My Understanding**  
Hierarchy exists but relationship rules are unspecified.

**Solution**  
Enforce one location -> one zone -> one warehouse. Capacity unit configured per location (`units`, `pallets`, `cubic_ft`).

## 18) Master Data Effective Dating
**Question**  
How are overlapping effective dates and backdated edits handled?

**My Understanding**  
Owner/supplier/carrier are effective-dated versioned records.

**Solution**  
Disallow overlap per entity key; allow backdated versions only if no closed transactions reference conflicting intervals.

## 19) Inventory Plan Assignment
**Question**  
Should task assignment be manual only or also auto-distributed?

**My Understanding**  
Distribution to staff is required; automation optional.

**Solution**  
Support manual assignment in v1 with optional auto-balancing by staff workload in v1.1.

## 20) Variance Threshold Scope
**Question**  
Is variance threshold evaluated per item/location line, per task, or per plan summary?

**My Understanding**  
Server enforcement likely expected at granular count line level.

**Solution**  
Evaluate threshold per counted line (`asset_type + location`), then roll up status to task and plan dashboards.

## 21) Corrective Action Requirements
**Question**  
What corrective action data is mandatory before closure approval?

**My Understanding**  
Closure requires corrective action and accountability acknowledgment.

**Solution**  
Require category, root cause, action description, owner, due date, and evidence attachment before reviewer approval.

## 22) Audit Trail Coverage
**Question**  
Which events must be immutable and queryable for audit?

**My Understanding**  
Security-sensitive and operationally critical events must be captured.

**Solution**  
Audit log must include auth events, role changes, unmask views, export actions, trip/version edits, inventory closures, job actions.

## 23) Request Signing Key Provisioning
**Question**  
How are request signing keys created, distributed, rotated, and revoked offline?

**My Understanding**  
Signing is mandatory but lifecycle is not defined.

**Solution**  
Use per-client key IDs with HMAC secrets provisioned by admin console; quarterly rotation; immediate revoke list in DB.

## 24) Trusted Time Source
**Question**  
Without internet NTP, what clock source is authoritative for 5-minute nonce validity?

**My Understanding**  
Clock drift between hosts can break request validation.

**Solution**  
Designate local NTP/time server appliance; allow +/- 90 sec skew; alert admins on excessive drift.

## 25) Rate Limiting Scope
**Question**  
Should rate limits apply per username, IP, device fingerprint, or combined?

**My Understanding**  
A combined strategy reduces bypass risk.

**Solution**  
Apply layered limits: per username + per IP/subnet; stricter limits on admin endpoints.

## 26) Offline CAPTCHA Design
**Question**  
What CAPTCHA mechanism is acceptable fully offline and accessibility-compliant?

**My Understanding**  
External CAPTCHA services cannot be used.

**Solution**  
Implement local challenge set (image + audio fallback), rotate challenge bank, and include accessibility alternatives.

## 27) Account Lockout Semantics
**Question**  
Do failed login counters reset on success or after lockout period only?

**My Understanding**  
Prompt specifies lock at 10 failures for 15 minutes.

**Solution**  
After 5 failures show CAPTCHA; at 10 consecutive failures lock 15 minutes; reset consecutive count on successful login.

## 28) Encryption Key Management
**Question**  
Where is AES-256 key stored and how is it protected locally?

**My Understanding**  
Key is local, but storage protection is unspecified.

**Solution**  
Use OS keychain/TPM where available; fallback encrypted key file with passphrase split-custody procedure.

## 29) Key Rotation and Re-encryption
**Question**  
How often are encryption keys rotated and how are existing records re-encrypted?

**My Understanding**  
Lifecycle must be defined for long-term security.

**Solution**  
Rotate annually or on incident; background re-encryption job supports checkpoint/resume and verification.

## 30) Backup and Restore Objectives
**Question**  
What RPO/RTO targets apply to nightly dumps and recovery operations?

**My Understanding**  
Nightly encrypted backups retained for 30 days are required.

**Solution**  
Set RPO <= 24h and RTO <= 4h; perform monthly restore drills and log evidence in admin console.

## 31) Backup Key Custody
**Question**  
Who can decrypt backups and how is key access controlled?

**My Understanding**  
Backup encryption is required but access policy is undefined.

**Solution**  
Require two-person approval for backup key retrieval; all decrypt operations audited.

## 32) Queue Delivery Guarantees
**Question**  
Should offline job execution guarantee exactly-once or at-least-once processing?

**My Understanding**  
At-least-once is realistic with retries and worker failures.

**Solution**  
Adopt **at-least-once** with idempotent job handlers and dedupe keys for manifests/attachments.

## 33) Job Dependency Cycles
**Question**  
How should circular dependencies in job definitions be handled?

**My Understanding**  
Dependency graph validation should prevent deadlock.

**Solution**  
Reject cycle creation at submit time with explicit dependency path in error response.

## 34) Checkpoint/Resume Boundaries
**Question**  
What unit of progress should checkpoints use (file, row, attachment)?

**My Understanding**  
Resumability is required for long-running ingest operations.

**Solution**  
Checkpoint by file + row offset + attachment index with periodic commits every N records.

## 35) Worker Lease/Heartbeat
**Question**  
How do distributed workers claim and recover abandoned jobs safely?

**My Understanding**  
MySQL queue table is shared by workers on multiple machines.

**Solution**  
Use lease-based locking with heartbeat; reclaim stale leases after timeout and increment retry count.

## 36) CSV Schema Governance
**Question**  
How are CSV formats versioned and validated across organizations and data sources?

**My Understanding**  
Manifest ingest requires predictable schemas and validation handling.

**Solution**  
Maintain schema registry table with versioned definitions and per-source validation rules.

## 37) Partial Ingest Error Policy
**Question**  
If part of a file is invalid, should valid rows still ingest?

**My Understanding**  
Operational workflows often need partial acceptance with traceable errors.

**Solution**  
Allow partial ingest by default; invalid rows routed to error report and correction queue.

## 38) Attachment Deduplication
**Question**  
How should duplicate files/images be detected and handled?

**My Understanding**  
Repeated scans may pick up unchanged files.

**Solution**  
Compute SHA-256 content hash and source path signature; skip or link duplicate payloads idempotently.

## 39) Anomaly Alert Thresholds
**Question**  
What numeric thresholds define repeated failed logins, job failure spikes, and bulk exports?

**My Understanding**  
Alert categories are defined, but trigger thresholds are not.

**Solution**  
Set baseline thresholds per org with defaults (e.g., 20 failed logins/15m, 2x failure rate hour-over-hour, >500 records export).

## 40) Data Export Scope by Role
**Question**  
What data can each role export, and in what formats?

**My Understanding**  
Self-service export is required, but least privilege must be maintained.

**Solution**  
Define role-based export bundles (CSV/JSON), with PII masking unless explicit privileged approval is present.

## 41) Account Deletion Semantics
**Question**  
Does account deletion mean full purge, soft delete, or anonymization with retained operational records?

**My Understanding**  
Retention notice implies some data may remain for legal/operational reasons.

**Solution**  
Implement deletion as deactivation + PII anonymization after retention window; preserve audit/transaction records.

## 42) Compliance Baseline
**Question**  
Which compliance frameworks must the system satisfy (e.g., HIPAA/privacy regulations)?

**My Understanding**  
Senior-care context likely implies elevated privacy/security obligations.

**Solution**  
Document a compliance baseline per deployment region and map controls to technical requirements before build finalization.

## 43) Accessibility Requirements
**Question**  
What accessibility standard and usability expectations apply for senior users?

**My Understanding**  
Interface should support older users with readable, navigable interactions.

**Solution**  
Target WCAG 2.1 AA with larger text presets, strong contrast options, keyboard navigation, and screen reader support.

## 44) Localization Requirements
**Question**  
Is multilingual support required from day one?

**My Understanding**  
Regional operators may require multiple languages.

**Solution**  
Internationalize UI strings and dates from v1, ship English initially, enable additional locale packs per organization.

## 45) Performance and Scale Targets
**Question**  
What are expected user counts, concurrent sessions, and API/job throughput targets?

**My Understanding**  
No concrete non-functional targets are currently specified.

**Solution**  
Define SLOs (e.g., p95 API < 400 ms on LAN, support 500 concurrent users/org, job queue latency < 60 s).

## 46) Acceptance Criteria and Test Gates
**Question**  
What exact acceptance tests are required before sign-off?

**My Understanding**  
Critical flows need explicit testable criteria.

**Solution**  
Create UAT matrix covering auth/security, trip booking/version re-ack, inventory variance closure, job retries/checkpoints, and backup/restore.
