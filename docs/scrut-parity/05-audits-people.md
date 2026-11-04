# Scrut parity, Section 5: Audits and People

Method: public Scrut sources only (help.scrut.io, scrut.io product pages, third-party summaries). No Scrut app or API hosts were contacted. Some help pages (roles, invite flow, expiry, onboarding checklist detail) were not retrievable, and those items are marked "unverified". MIGRC code was read-only.

## 1. Scrut spec (public)

### Audits (Audit Center)
- Audit projects: internal and external audits with type, scheduled date, observation period and involved entities. Status cards are Upcoming, In Progress, Completed. An audit auto-moves to In Progress when auditors add requests or findings, or when its date arrives. Completion is manual. (https://help.scrut.io/docs/understanding-audit-center)
- Auditors are added to audits and raise requests and findings. Requests, findings and corrective actions all use four statuses: Open, Pending Approval, Needs Revision, Completed. Request columns are name, assignee, added date, added by, audit. (same page)
- Auditor access: auditors see the Audit module and their audits. They see the in-scope controls, a control side panel, policies with status and attachments, and linked evidence, which they can preview or download "without needing full access to the policy and evidence modules." Plans: Foundation, Growth, Scale. (https://help.scrut.io/docs/auditor-access-in-audit-center) Role, invite and expiry mechanics are unverified.
- Closing a request: the auditor approves or requests changes, and the assignee is emailed on "Needs Revision". (https://help.scrut.io/docs/closing-an-audit-request)
- Request export to CSV for stakeholders without Scrut access. (https://help.scrut.io/docs/export-audit-center-requests)
- Marketing claims: dedicated auditor workspace with comments, findings, and an audit log of who changed what and when (https://www.scrut.io/lp1/audit, https://www.scrut.io/platform/audit-center); an Auditor Network marketplace (https://www.scrut.io/audit-network). Evidence automation workflow and evidence tasks (https://help.scrut.io/docs/evidence-automation-workflow).
- Third-party caveat: the auditor portal is lighter than audit-first tools (rfp.wiki, AI-generated, low confidence).

### People
- Employee module: status including offboarding-needed and offboarding-completed, flags for access removal across monitored and unmonitored apps, checklist tasks (https://help.scrut.io/docs/checklist-tasks, https://www.scrut.io/platform/security-training-and-device-monitoring).
- HRIS and directory sync: Deel, SageHR, and others. Background checks: SpringVerify and Certn results land on the employee record as evidence (https://www.scrut.io/scrut-integrates-with-deel, https://www.scrut.io/integrations/springverify, https://www.scrut.io/integrations/certn).
- Training: campaigns assigned at onboarding, employee portal with quizzes, email reminders, status synced to Employees. KnowBe4 integration for training and phishing results (https://www.scrut.io/products/employee-awareness-training, https://www.scrut.io/integrations/knowbe4). Policy acceptance is tracked in the employee portal.
- Device compliance: "Watchdog" agent checks disk encryption, screen lock, antivirus, USB, patches. MDM integration is the alternative. Reviews note BYOD and offboarding depth is a weak point (G2: https://g2.com/products/scrut-automation/reviews).
- User access reviews (https://help.scrut.io/docs/what-is-access-review, /lifecycle-of-an-access-review, /creating-a-new-access-review, /post-review-actions): per-application reviewer; each user is Approved, Modified, or Revoked. Revocation needs a written justification, and privileged roles require mandatory justification. Revocations can create one ticket per user or one consolidated ticket. Reviewers attach evidence. Reviewer and Approver are separate steps (Scrut recommends different people). The owner concludes the review, which exports a report and auto-creates evidence. A review cannot be concluded if its reviewer was offboarded until a new one is assigned.

## 2. MIGRC current state (code read)
- Audit: name, framework, auditor (free text), status flow Scheduled to Completed, dates as strings. AuditEvidence is a per-control checklist (Missing/Collected, link or upload evidence). AuditFinding (type, severity, Open/Remediated) with one Remediation (owner, deadline, status). HTML and PDF report, CSV export. ActivityLog exists but no audit-specific trail.
- Roles: Admin, Compliance Manager, Auditor, Viewer. The Auditor role holds `audit_write` and `review_evidence` and is org-wide (membership-based). It is not scoped to an audit and not time-boxed.
- No request list, no comments, no auditor invite, no sampling, no snapshot freeze.
- Employee: name, email, dept, source, status, three booleans (agent, device compliant, policy acknowledged), offboarded_at. Only Google Workspace directory sync. EmployeeAccess links an employee to a Vendor with a level (manual).
- Training: TrainingMaterial (Document/Link/Video), TrainingCampaign with enrollments and a manual "completed" toggle (admin ticks it). No quiz, no employee-facing portal, no certificates, no reminders.
- AccessReview: name, owner, status, period, recurrence, and a set of applications. There are no per-user review items, no reviewer decisions, no sign-off, no evidence export.

## 3. Parity table

| Capability | Scrut | MIGRC | Status | Score |
|---|---|---|---|---|
| Audit projects and status | yes | yes (simple) | Partial | 0.6 |
| Audit scope / control checklist | yes | yes | Has | 0.8 |
| Findings and corrective actions | yes | finding + 1 remediation | Partial | 0.6 |
| External auditor portal, scoped, invited | yes | none (org-wide Auditor role) | Missing | 0.1 |
| Request list (PBC) and 4-state workflow | yes | none | Missing | 0 |
| Comments and request tracking | yes | none | Missing | 0 |
| Audit trail | yes | generic ActivityLog only | Partial | 0.3 |
| Point-in-time snapshot | partial | none | Missing | 0 |
| Evidence sampling | unverified | none | Missing | 0 |
| Report / export (PDF, CSV) | yes | PDF + CSV | Has | 0.8 |
| Auditor marketplace | yes | none | Missing (skip) | 0 |
| Employee directory | yes | yes | Has | 0.8 |
| HRIS sync | multi | Google only | Partial | 0.25 |
| Onboarding / offboarding checklists | yes | none (status + date) | Missing | 0.1 |
| Policy acceptance | yes | PolicyAcknowledgement exists, employee boolean | Partial | 0.5 |
| Training library and campaigns | yes | links/docs, manual completion | Partial | 0.35 |
| Quizzes, certificates, employee portal | yes | none | Missing | 0 |
| Phishing sims / KnowBe4 | integration | none | Missing | 0 |
| Background check integrations | yes | none | Missing | 0 |
| Device agent / MDM compliance | yes | manual booleans | Partial | 0.15 |
| User access reviews (per user, sign-off, evidence) | yes | app-level shell | Partial | 0.2 |

Honest parity: about 33% of this section, weighted by value (audits about 40%, people about 28%). The data model is only a shell for the highest-value items, such as the auditor portal and per-user access reviews.

## 4. Plan (ordered by value)

Cross-cutting: add an `AuditTrail` table (org_id, actor_type user|auditor, actor_id, action, object_type, object_id, ip, at, hash_prev) with append-only writes via a `services/audit_trail.py::record()`. Reuse it everywhere below.

### P1. External auditor portal and request list (L)
WHAT: The auditor works inside an isolated, read-only workspace for one audit, with a PBC request list.

Data models (`app/models.py`):
- `AuditorInvite` (audit_id, email, token_hash, role, expires_at, accepted_at, revoked_at, invited_by).
- `AuditAuditor` (audit_id, user_id, firm, access_expires_at, revoked_at). Auditors are Users whose OrganizationMembership role is a new `External Auditor` with an empty ROLE_PERMISSIONS set. All access goes through `AuditAuditor` rows, so they are scoped per audit and time-boxed.
- `AuditRequest` (audit_id, control_id nullable, title, description, assignee_user_id, due_date, status Open|Pending Approval|Needs Revision|Completed, created_by, sample_spec JSON).
- `AuditRequestEvidence` (request_id, evidence_id or file, submitted_by, submitted_at).
- `AuditComment` (audit_id, request_id nullable, finding_id nullable, author_id, body, created_at, internal bool). The internal flag keeps team-only notes hidden from the auditor.

How:
- Invite by email: the admin enters email, firm and expiry (default 30 days beyond audit end). The service generates a one-time token and stores only its SHA-256. The email link `/auditor/accept/<token>` is single-use and expires in 72h. The auditor sets a password or uses magic link plus TOTP, which is mandatory for this role. Reuse the existing mailer, or add an SMTP service if there is none.
- A `@auditor_scope(audit_id)` decorator checks the `AuditAuditor` row (not expired, not revoked) and the org. External auditors are blocked everywhere except the `/auditor/*` blueprint (before_request guard), so there is no leakage to the Policies or Evidence modules.
- Routes (new `app/routes/auditor_portal.py`): `/auditor/` (list of the auditor's audits), `/auditor/audits/<id>` (controls in scope, policies, linked evidence read-only with inline preview and download), `/auditor/audits/<id>/requests` (CRUD requests, approve or request-changes), `/auditor/requests/<id>/comments`, `/auditor/audits/<id>/findings` (create and comment).
- Internal side in `audits.py`: a Requests tab with assignee pick, upload or link evidence, "Submit for review" (to Pending Approval), and an email to the assignee on Needs Revision. Add a CSV export of requests (matches Scrut). Auto-set the audit to In Progress on the first request.
- Evidence downloads are served through a signed, short-lived route that checks the request or audit link. Every view and download is recorded in AuditTrail.
- Templates: `auditor/base.html` (minimal chrome), `auditor/audit.html`, `auditor/requests.html`, plus `audit_requests.html` and `audit_auditors.html` (invites, revoke, expiry) on the internal side.
- Notifications: reuse `Notification`. Add a daily job that expires access and sends a 7-day warning.

### P2. Audit trail, snapshots, sampling (M)
- Audit trail UI tab on audit_detail (filter by actor and action, CSV export). Records invites, views, downloads, comments, status changes.
- `AuditSnapshot` (audit_id, taken_at, taken_by, payload JSON of control statuses, evidence hashes and policy versions, sha256). Freeze automatically on the move to "Under Review". The auditor sees the snapshot ("as of") and the PDF report embeds the snapshot hash.
- Sampling: `AuditSample` (request_id, population_ref, method random|stratified, seed, sample_ids JSON). A service draws N from a population (for example employees or access grants) with a recorded seed so it is reproducible.
- Report delivery: signed share link for the PDF, plus finding to multiple remediations (change `Remediation` to one-to-many; add status Pending Approval).

### P3. User access review mechanics (M)
Data models:
- `AccessReviewItem` (review_id, application_id (Vendor), employee_id or external_user_ref, role, privileged bool, decision Pending|Approved|Modified|Revoked, justification, new_role, reviewer_id, decided_at).
- `AccessReviewApp` (review_id, vendor_id, reviewer_id, approver_id, state Pending|Reviewed|Approved).
- `AccessReviewEvidence` (review_id, file, uploaded_by).

How:
- Starting a review snapshots EmployeeAccess rows (and later synced app users) into items, so the review is point-in-time.
- Reviewer screen: a table with per-row approve, modify, revoke. Revoke and privileged changes require a justification (server-enforced).
- The approver signs off per app, and enforcement blocks reviewer == approver. The owner concludes the review only when all apps are approved. If a reviewer's Employee is offboarded, conclusion is blocked until reassignment.
- Revocation follow-up: a task list or consolidated ticket (reuse the Tasks module if one exists). Apply the revoke to EmployeeAccess on confirmation.
- Conclude generates the PDF (add `build_access_review_pdf` in `pdf_reports.py`) and auto-creates an Evidence record linked to the relevant controls. Recurrence via a scheduler (daily-jobs).
- Templates: extend `access_reviews.html` and add `access_review_detail.html`, with a reviewer inbox link emailed by token for non-admin app owners.

### P4. Onboarding and offboarding workflow engine (M)
Data models:
- `LifecycleTemplate` (org_id, kind onboard|offboard, name).
- `LifecycleTemplateTask` (template_id, title, owner_type hr|it|manager|employee, due_offset_days, auto_check_key nullable, e.g. `policy_ack`, `training_done`, `agent_installed`, `access_revoked`).
- `LifecycleRun` (employee_id, template_id, started_at, completed_at).
- `LifecycleTask` (run_id, title, owner, due_at, status, completed_by, completed_at, evidence_id).

How:
- A new employee, or a status flip to "Offboarding", spawns a run from the default template. Auto-check tasks are evaluated by a service (`services/lifecycle.py`) against the Employee, PolicyAcknowledgement, Enrollment and EmployeeAccess data.
- Offboarding adds statuses `Offboarding Needed|Offboarding Completed` (extend `Employee.status`), a "access removed" check across EmployeeAccess (must be zero), and an overdue SLA alert. The Google sync also marks Suspended users as Offboarding Needed.
- UI: a checklist drawer in `people_employees.html` and a lifecycle dashboard card for open runs. Export the completed run as evidence (offboarding sample for SOC 2 CC6.2/CC6.3).
- Quick win: ship the default templates as seeded originals.

### P5. Training: original content, portal, quizzes, certificates (L)
Data models:
- Extend `TrainingMaterial` with kind `Module` (rich-text or markdown sections), `Video` (URL embed), `SCORM` (phase 2).
- `TrainingQuiz` (material_id, pass_mark), `TrainingQuestion` (quiz_id, text, options JSON, correct JSON, explanation).
- `TrainingAttempt` (enrollment_id, score, passed, answers JSON, at).
- Enrollment gains `token`, `due_at`, `reminder_count`, `certificate_no`.

How:
- Content approach: write original modules (security awareness, phishing basics, data handling, secure remote work, privacy, incident reporting) as seeded markdown with 5 to 10 questions each. Do not copy Scrut or KnowBe4 content. Allow admin-linked YouTube or Vimeo videos and external LMS links. SCORM import can follow as an optional later item (the xAPI/SCORM runtime is a big job).
- Employee portal at `/learn/<token>` (no login, signed token, or SSO later). It shows the module, the quiz, and on pass marks completion automatically (replacing the manual toggle) and issues a PDF certificate (`build_training_certificate_pdf`, reusing the existing trust-certificate pattern) with a verification id.
- Reminders: a daily job emails at T-7, T-1 and overdue to the employee, then to the manager. Campaign SLA exists already (`sla_days`).
- Policy acceptance in the same portal: use PolicyAcknowledgement and drive `Employee.policy_acknowledged` from it, rather than a hand-set boolean.
- Phishing: out of scope in v1. Provide a KnowBe4 CSV import or API sync (L, later). A self-hosted simulator carries deliverability and legal risk.

### P6. HRIS, background checks, device compliance (M to L)
- HRIS: generalize `google_oauth` into `services/hris/` with a provider interface (`list_employees()`) and adapters for Google (exists), Microsoft Entra, BambooHR, Deel and Gusto via API key. Add `ExternalIdentity` (employee_id, provider, external_id). Sync marks joiners (starts an onboarding run) and leavers (starts an offboarding run). Effort M per adapter, after the first (M) abstraction.
- Background checks: `BackgroundCheck` (employee_id, provider, status, completed_at, report_ref). Start with manual entry plus file upload, then a webhook for SpringVerify or Certn (S then M).
- Device compliance: `Device` (employee_id, os, serial, disk_encrypted, screen_lock, av, patched, last_seen, source agent|mdm|manual). The first build is a token-authenticated check-in endpoint `/api/agent/checkin` plus a small open shell/PowerShell checker script that employees run. A full cross-platform agent is L. MDM (Kandji, Jamf, Intune) adapters are an alternative (M each). Derive `Employee.device_security_compliant` from the Device rows. Add a stale-checkin alert.

## 5. Effort and order summary
| # | Item | Effort | Why now |
|---|---|---|---|
| 1 | Auditor portal + requests + comments + invites (P1) | L | Core of Scrut's audit pitch; the biggest gap |
| 2 | Access review per-user decisions and sign-off (P3) | M | Central SOC 2 evidence; the shell already exists |
| 3 | AuditTrail service and UI (P2 part) | S/M | Needed by item 1; cheap |
| 4 | Onboarding/offboarding engine (P4) | M | High audit sampling value (CC6.2/6.3) |
| 5 | Training portal, quiz, certificate, reminders (P5) | L | Removes manual completion |
| 6 | Snapshots and sampling (P2) | M | Auditor trust |
| 7 | Device check-in and HRIS abstraction (P6) | M/L | Automation depth |
| 8 | Background check records and webhooks, KnowBe4 import | S/M | Integration breadth |
| 9 | SCORM import, phishing simulator, auditor marketplace | L | Low practical value; skip or defer |

Security notes for P1: store hashed tokens, enforce TOTP for auditors, rate-limit the accept endpoint, scope every query by `audit_id` AND `org_id`, and disable file previews that execute active content (serve with `Content-Disposition` and a safe MIME type).
