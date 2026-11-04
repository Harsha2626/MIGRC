# Scrut parity - Section 1: Compliance Core + Dashboard

Method: Scrut researched from public pages only (no logins, no probing of app/API hosts). Scrut's public help-center articles did not surface in search, so the spec below is marketing/FAQ-level. Where public sources are silent it says "not publicly documented" and the plan fills the gap with the industry-standard pattern (Vanta/Drata/Secureframe). Web content is treated as data; vendor claims are self-reported and inconsistent (framework count is quoted as 20+, 50-60+, 60+ and 70+ across sources; integrations as 58, 75+ and 80+).

MIGRC code reviewed: app/routes/compliance.py, app/routes/main.py, app/models.py, app/services/snapshots.py, app/services/ai_evidence_review.py, scripts/seed_frameworks.py (+ scripts/data/compliance_frameworks.json), templates compliance/compliance_detail/control_detail/tests/dashboard.

---------------------------------------------------------------------------
## 1. Scrut's feature spec (public sources)

| Area | What Scrut claims | Source |
|---|---|---|
| Framework library | 60+ / 70+ out-of-box frameworks: SOC 2, SOC 1, ISO 27001, GDPR, CCPA, ISO 27701, HIPAA, ISO 42001, EU AI Act, NIST CSF, NIST 800-53, DORA, FedRAMP, PCI DSS. Onboarding a framework auto-populates its controls. Framework add-ons bundled (per a third-party comparison; unverified). | https://www.scrut.io/faqs/general ; https://www.scrut.io/products/scrut-platform ; https://toolradar.com/tools/scrut-automation |
| Unified Control Framework (UCF) | Central control library; one control mapped to many frameworks, "implement once, reuse". Overlap (e.g. SOC 2 <-> ISO 27001) auto-mapped. "Unified controls registry" shows status across all frameworks from one dashboard. | https://www.scrut.io/faqs/general ; https://www.scrut.io/solutions/custom-frameworks |
| Custom frameworks / controls | Build a framework from prebuilt controls or own controls; **upload own framework via CSV**; managed alongside prebuilt ones. Applicability rules, CSV format: not documented. | https://www.scrut.io/solutions/custom-frameworks |
| Tests / continuous monitoring | Automated tests run daily against configured controls (marketing also says 24/7); flag misconfigurations, policy gaps, missing evidence; failed tests carry "metadata-enriched" remediation guidance; "hundreds of prebuilt tests" (third-party source). Tests attach to controls and are driven by integrations. | https://www.scrut.io/faqs/general ; https://www.scrut.io/products/scrut-platform ; https://ismscopilot.hc.ferndesk.com/how-to-use-isms-copilot-with-scrut-617fk |
| Evidence collection | Automatic from 75-80+ integrations (cloud, endpoint, HR, IdP, code repos, ticketing, SIEM); >80% of SOC 2 evidence automated (claim). Manual upload for systems without integration (reviews). | https://www.scrut.io/hub/soc-2/soc-2-compliance-software ; https://www.trustradius.com/products/scrut-automation |
| Readiness / dashboards | Real-time dashboards per module and unified across frameworks (controls, evidence, tests, policies); custom filters and drill-down; org-level dashboards for multi-entity. | https://www.scrut.io/products/scrut-platform |
| Gap analysis | Tests + auto-mapping "detect gaps"; AI copilot (Scrut Teammates) gives contextual responses to compliance gaps. | https://www.scrut.io/ ; platform page |
| Tasks / workflow | Create, assign, track tasks; comments, tagging, instant alerts; bidirectional sync with Jira etc.; smart alerts for gaps and overdue tasks; remediation steps pushed to task tools. | platform page ; FAQ |
| Due dates / recurrence | Owners + deadlines on risks, mitigation plans, tasks; overdue alerts. Recurrence cadence for evidence/controls not publicly documented (daily test cadence only). | FAQ |
| Comments / change history | Commenting on tasks/controls; auditors comment on controls/evidence; permissions logged; reports include activity logs. | FAQ |
| Auditor access / exports | Audit Center: per-audit scoped read-only auditor role (controls, evidence, policy previews), auditor comments, findings, progress; "never unrestricted access"; audit projects with defined scope; downloadable audit-ready reports (control status, evidence summaries, timestamps, activity logs). | FAQ ; custom-frameworks page |
| RBAC / multi-entity | Admin, contributor, employee, auditor; per-department/module permissions; workspaces for business units reusing common-control docs. | platform page |
| AI | Scrut Teammates: AI risk insights, gap copilot. | https://www.scrut.io/ |

Not publicly verifiable: exact test catalog, per-test schedule options, control "applicability" logic, evidence-expiry/recurrence settings, auditor-portal UX.

---------------------------------------------------------------------------
## 2. MIGRC current state (from code)

- **Library**: 81 shared frameworks in scripts/data/compliance_frameworks.json (avg ~17 controls each, i.e. summarized, not clause-complete; e.g. PCI DSS 12 controls, COBIT 40). Opt-in via `OrganizationFramework`; private frameworks per org (`Framework.organization_id`). Add/delete framework routes. No CSV import. No cross-framework mapping: `Control.framework_id` is a hard 1:N, so SOC 2 CC6.1 and ISO A.5.15 are unrelated rows with separate ControlStatus and separate evidence mapping.
- **Control model**: shared definition (`Control`) + per-org `ControlStatus(status, owner[String name], updated_at)`. Statuses Passing/Failing/Not Assessed/Not Applicable. No due date, no recurrence, no description override, no applicability reason, no priority.
- **Tests**: `/tests` is a *view* that lists every control + policy as a "test" (Passing / Fix Required / Ignored). No test definitions, no automated execution, no integrations, no run history.
- **Evidence**: manual file upload only (pdf/png/jpg/csv/xlsx/doc/docx), `source_type` dropdown, audit period, multi-control mapping (`EvidenceMapping`), review Approve/Reject + AI metadata-only suggestion (`ai_evidence_review.py`, never reads file content). Status recalculation (`_recalculate_control_status`): any rejected -> Failing; any approved -> Passing; else Not Assessed. No evidence expiry/freshness, no URL/link/screenshot/auto evidence.
- **Dashboard**: weighted compliance score, per-framework cards, KPIs with 7-day deltas (ComplianceSnapshot/DashboardSnapshot), 30-day trend, risk matrix, 30-day deadlines (policy/vendor/audit/training), pending evidence count. Daily snapshots via `ensure_snapshots_for_today`.
- **Reports**: per-framework PDF (`/compliance/<id>/report.pdf`). Trust center with NDA, badge, certificate. Activity log (`ActivityLog`, `log_activity`) exists but control status changes are not logged individually.
- **Collaboration**: no comments on controls/evidence, no tasks, no notifications on control events (a `Notification` model exists elsewhere).
- Audit module (Audit, AuditEvidence, AuditFinding) is outside this section but is where auditor access should hook in.

---------------------------------------------------------------------------
## 3. Parity table

Scoring: Has = 1.0, Partial = 0.5, Missing = 0. Weights reflect user-visible importance (1-3).

| # | Feature | Wt | MIGRC | Notes |
|---|---|---|---|---|
| 1 | Framework library breadth (60+) | 2 | Has | 81 frameworks (depth is shallow) |
| 2 | Framework depth (full clause-level controls) | 2 | Partial | ~17 controls/framework |
| 3 | Add/remove framework per org | 1 | Has | |
| 4 | Custom (private) framework + manual controls | 2 | Partial | add_framework exists; no control authoring UI verified, no CSV upload |
| 5 | CSV framework/control import | 1 | Missing | |
| 6 | Unified control library / cross-framework mapping | 3 | Missing | biggest structural gap |
| 7 | Unified controls registry + multi-framework status view | 2 | Missing | |
| 8 | Control ownership | 2 | Partial | free-text name, not a user FK |
| 9 | Control applicability / N/A with justification | 1 | Partial | status exists, no reason |
| 10 | Control due dates / recurrence | 2 | Missing | |
| 11 | Test model (defined tests linked to controls) | 3 | Missing | `/tests` is derived view |
| 12 | Automated tests / continuous monitoring | 3 | Missing | no integrations |
| 13 | Test run history, failure remediation guidance | 2 | Missing | |
| 14 | Integrations-based evidence (cloud/HR/IdP/repo) | 3 | Missing | paid-API/credential dependent |
| 15 | Manual evidence upload + mapping | 2 | Has | |
| 16 | Evidence types (link, text, screenshot, policy-as-evidence) | 1 | Partial | file only |
| 17 | Evidence expiry / freshness / recurring collection | 2 | Missing | |
| 18 | Evidence review workflow | 1 | Has | + AI suggestion (Scrut has less) |
| 19 | AI gap/evidence assist | 1 | Has | metadata-only |
| 20 | Readiness dashboard (score, trend, per-framework) | 3 | Has | |
| 21 | Dashboard drill-down / custom filters / widgets | 1 | Partial | |
| 22 | Gap analysis view (failing/unassessed by framework, effort) | 2 | Partial | per-control only |
| 23 | Task assignment on controls/tests | 3 | Missing | |
| 24 | Comments / tagging on controls & evidence | 2 | Missing | |
| 25 | Alerts/notifications (overdue, failing) | 2 | Missing | |
| 26 | Change history / audit trail per control | 2 | Partial | evidence events logged; control status not |
| 27 | Auditor-ready export (PDF) | 2 | Partial | PDF per framework; no evidence ZIP/CSV |
| 28 | Auditor read-only scoped portal / audit projects | 2 | Missing | (Audit module may cover; verify in section 2/3) |
| 29 | Ticketing sync (Jira) | 1 | Missing | credential dependent |
| 30 | Multi-entity workspaces | 1 | Partial | multi-tenant orgs, no parent/child roll-up |

Weighted score: earned = 2+1+1+1+1+0.5*... computed: Has items (1,3,15,18,19,20) = 2+1+2+1+1+3 = 10; Partial items (2,4,8,9,16,21,22,26,27,30) weights 2+2+2+1+1+1+2+2+2+1 = 16 -> 8; total possible = 54+... sum of all weights = 2+2+1+2+1+3+2+2+1+2+3+3+2+3+2+1+2+1+1+3+1+2+3+2+2+2+2+2+1+1 = 58. Earned 18/58.

**Honest parity: ~31%** (about 45% if scoped to "manual GRC workflow" only; ~0% of the automation layer that is Scrut's core differentiator).

---------------------------------------------------------------------------
## 4. Plan to reach ~100% practical parity (ordered by value)

Conventions: Flask-SQLAlchemy models in app/models.py; additive migration (project has no Alembic confirmed - use `db.create_all()` plus idempotent `ALTER TABLE` helper script like scripts/seed_*). Services under app/services/. Blueprint: app/routes/compliance.py (split new routes into app/routes/controls.py, app/routes/tests_engine.py to avoid a 1000-line file).

### G1. Unified control library / cross-framework mapping (L) - highest value
- WHAT: Implement a control once; it satisfies requirements in many frameworks. Control page shows "Also satisfies: SOC 2 CC6.1, ISO A.5.15, HIPAA 164.312(a)". Passing one control flips all mapped framework requirements. Framework page lists requirements with their mapped unified control. Evidence uploaded once counts everywhere.
- HOW: Split "requirement" from "control".
  - Keep existing `Control` rows as framework *requirements* (no destructive change).
  - New `UnifiedControl(id, organization_id NULL=shared, ucf_code, title, description, category, test_criteria, evidence_requirement, default_recurrence_days)`.
  - New `RequirementMapping(id, control_id FK controls, unified_control_id FK, strength ['full','partial'], source ['seed','ai','manual'], confidence)`; unique(control_id, unified_control_id).
  - `ControlStatus` becomes per (org, unified_control) via new `UnifiedControlStatus(org_id, unified_control_id, status, owner_user_id, due_date, recurrence_days, last_reviewed_at, na_reason)`. Requirement status is *derived*: Passing iff all mapped unified controls (strength full) Passing; existing ControlStatus rows remain for unmapped requirements (backward compatible).
  - `EvidenceMapping` gains `unified_control_id` nullable; `for_org` unchanged.
  - Seeding algorithm: build the UCF by clustering requirements. Step 1: embed requirement title+description (local model via ai_dispatch or sentence-transformers if available), cosine > 0.82 -> candidate pairs. Step 2: AI review each candidate cluster with the existing ai_dispatch (JSON: same/partial/different). Step 3: use public crosswalks to seed ground truth: NIST CSF<->800-53 (NIST OLIR), ISO 27001 Annex A<->NIST 800-53 (ISO/NIST published mappings), SCF (Secure Controls Framework, CC BY-ND license: verify terms before bundling; use as reference only), CIS Controls->ISO/NIST mappings (CIS publishes). Store as `scripts/data/ucf_mappings.json`; human-curated overrides win.
- WHERE: app/models.py (3 tables); new app/services/ucf.py (`derive_requirement_status(org, control)`, `propagate(org, unified_control_id)` called from `_recalculate_control_status`); scripts/build_ucf.py + scripts/seed_ucf.py; routes `GET /controls` (registry), `GET /controls/<id>`, `POST /controls/<id>/map`; templates controls_registry.html, update control_detail.html and compliance_detail.html; Framework.to_dict score logic.
- Deps: none; unlocks G3, G4, G6. Quality of mappings is the real cost (curation), not code.

### G2. Task model + assignment + comments + notifications (M)
- WHAT: Any failing control/test/evidence gap becomes a task with assignee, due date, status, priority; comment thread with @mentions on controls, evidence, tasks; bell/email alerts for assigned, overdue, failing; "My tasks" page.
- HOW: `Task(id, organization_id, title, description, status[open/in_progress/blocked/done/ignored], priority, assignee_user_id, due_date, created_by, entity_type, entity_id, source['manual','test_failure','evidence_expiry','auto'], external_ref, closed_at)`; `Comment(id, organization_id, entity_type, entity_id, user_id, body, mentions JSON, created_at, edited_at)`. Reuse existing `Notification`. Daily job (extend scripts/scheduled-jobs per docs/scheduled-jobs.md) marks overdue and fan-outs notifications.
- WHERE: new app/routes/tasks.py (`/tasks`, `/tasks/<id>`, `POST /api/comments`), app/services/tasks.py, templates tasks.html, partial _comments.html included in control_detail.html and evidence rows; nav link; dashboard "My open tasks" tile.
- Deps: none. Effort M.

### G3. Real test model + execution engine (L)
- WHAT: `/tests` lists defined tests (e.g. "MFA enabled for all users", "Policy reviewed in last 12 months", "Evidence not older than 90 days") with last-run time, pass/fail, history, remediation text, linked controls; "Run now"; daily scheduled run; failing test auto-creates task and flips mapped control to Failing.
- HOW: `TestDefinition(id, key, name, description, category, check_type['internal','integration','script'], handler, params JSON, severity, remediation_md, default_schedule_cron, shared)`; `TestControlLink(test_id, unified_control_id)`; `OrgTest(org_id, test_id, enabled, schedule, ignore_reason, ignored_until)`; `TestRun(id, org_id, test_id, started_at, status[pass/fail/error/skipped], details JSON, resources_checked, resources_failing)`. Handler registry in app/services/tests/ (decorator `@register_test('policy.reviewed_12mo')`). Control status rule: control Passing only if all linked enabled tests pass AND required evidence approved; otherwise Failing.
- **Internal tests buildable now with zero third-party access** (data already in MIGRC): policy published/reviewed within N months, policy acknowledged by >=X% employees, training campaign completion, access review completed in period, vendor assessment current, risk treatment overdue, asset inventory owner set, evidence not expired, open critical incident, employee offboarding access removed (Employee/EmployeeAccess models), device records (Asset). ~30-40 such tests are practical.
- WHERE: models.py; app/services/test_engine.py (`run_all(org)`, `run_test(org, test)`), app/services/tests/*.py handlers; routes in app/routes/compliance.py replacing `tests()` (`GET /tests`, `GET /tests/<id>`, `POST /tests/<id>/run`, `POST /tests/<id>/ignore`); templates tests.html (reuse filter UI), test_detail.html; cron entry; scripts/seed_tests.py.
- Deps: G1 (links), G2 (task creation). Effort L.

### G4. Integrations framework for automated evidence/tests (L, partly infeasible)
- WHAT: Connect AWS/GCP/Azure, Google Workspace/Okta/Entra, GitHub/GitLab, Jira, HRIS, MDM; collected configs become evidence and feed tests.
- HOW: `Integration(id, org_id, provider, status, config_encrypted, last_sync_at, last_error)`, `IntegrationResource(id, org_id, integration_id, resource_type, external_id, data JSON, fetched_at)`; connector base class `app/services/integrations/base.py` (`sync(org)->resources`); auto-evidence writer creates `Evidence(source_type='Integration', ...)` + `EvidenceMapping`, with `collected_at`. Encrypt secrets with Fernet key from env. Existing `GoogleWorkspaceConnection` model is the template.
- WHERE: models.py, app/services/integrations/{aws,github,google_workspace,okta,jira}.py, app/routes/integrations.py (`/integrations`, OAuth callback routes), templates integrations.html.
- Feasibility: connectors are buildable with customers' own read-only credentials (boto3, GitHub REST, Google Admin SDK, Okta API all free to call with the customer's own keys). Infeasible/low practical value: Scrut's *breadth* (80+ maintained connectors, SOC-2-vetted OAuth app approvals, e.g. Google/Slack/Atlassian marketplace app review, MDM vendors needing partner programs). Target 8-10 connectors (AWS, GCP, Azure, GitHub, Google Workspace, Okta, Entra, Jira, Slack, BambooHR) = practical parity for typical SMB. Per connector effort M.
- Deps: G3 (tests consume resources).

### G5. Control due dates, recurrence, evidence expiry (S-M)
- WHAT: Each control and evidence item has next-due date; recurring tasks regenerate (annual access review, quarterly vuln scan); evidence marked "Expiring/Expired" after validity window, and control reverts to Not Assessed/Failing; dashboard deadline panel includes control/evidence deadlines.
- HOW: add columns to `ControlStatus` (or `UnifiedControlStatus`): `due_date`, `recurrence_days`, `last_reviewed_at`; `Evidence.valid_until`, `Evidence.collected_at`. Update `_recalculate_control_status` to ignore evidence with `valid_until < today`. Add handler test `evidence.fresh`. Extend `_build_upcoming_deadlines` in app/routes/main.py.
- WHERE: models.py, compliance.py (`_recalculate_control_status`, upload form fields `valid_until`), control_detail.html, dashboard.html deadline list, daily job.
- Deps: none (G2 for task regeneration). Effort S-M. Do this early as it is cheap.

### G6. Gap analysis / readiness view (M)
- WHAT: Per framework "Readiness" page: % ready, breakdown by control category/domain, list of gaps sorted by impact (controls blocking most frameworks, by tests failing, missing evidence), estimated effort, "fix this first" ranking, and AI summary per gap with remediation steps.
- HOW: service `app/services/readiness.py`: `gaps(org, framework)` returns missing-evidence, failing-test, unowned, overdue buckets; impact = number of frameworks a unified control satisfies (G1) x severity; effort from control metadata (`effort_hours` seed field). AI remediation text via ai_dispatch (cache in `GapInsight` table keyed by (org, control, hash(state))).
- WHERE: new route `GET /compliance/<fw_id>/readiness` + `GET /readiness` (cross-framework), templates readiness.html (reuse kpi tiles + category bars), dashboard.html link/"top gaps" widget.
- Deps: G1 helpful, G3 for test-based gaps; manual-only version possible now (S). Effort M.

### G7. Control change history (S)
- WHAT: Timeline on control page: status changes, owner changes, evidence added/approved, test runs, comments; filterable; included in exports.
- HOW: write `ControlEvent(id, org_id, control_id, unified_control_id, actor_user_id|null, event_type, old_value, new_value, detail JSON, created_at)` from a single helper `set_control_status()` that all code paths must use (replace direct `row.status =` in `_recalculate_control_status`). Also keep `log_activity` call.
- WHERE: models.py, compliance.py, control_detail.html tab "History".
- Deps: none. Effort S.

### G8. Auditor-ready exports + scoped auditor access (M)
- WHAT: (a) "Audit package" ZIP: framework report PDF, control matrix CSV (control, status, owner, evidence list, test results), evidence files in per-control folders with manifest + SHA-256, activity log; period-filtered. (b) Auditor role: invite by email, read-only access scoped to selected frameworks/audit, can comment and raise requests/findings on controls and evidence, all access logged; link to the existing Audit/AuditFinding models.
- HOW: `AuditorGrant(id, org_id, audit_id, user_id, framework_ids JSON, expires_at, created_by)`; `AuditRequest(id, audit_id, control_id, evidence_id, requested_by, status, due_date, note)`; add `role='auditor'` to OrganizationMembership permission map with module whitelist enforced in `require_permission`; export service app/services/audit_package.py using zipfile + existing PDF generator.
- WHERE: new app/routes/auditor.py (`/auditor/...` read-only views reusing control_detail with `readonly=True`), `GET /compliance/<id>/audit-package.zip`, `GET /compliance/<id>/controls.csv`; templates auditor_home.html; update framework_report_pdf to include evidence summary, test results, activity.
- Deps: G7 (history in export), G3 (test results). Effort M.

### G9. Custom frameworks + CSV import + control authoring (S-M)
- WHAT: Upload CSV (code,title,description,category,[mapped_ucf_codes]) to create a private framework; edit/add/delete controls; clone a shared framework and customize; per-org requirement applicability toggle with reason.
- HOW: importer service with validation/preview step (dry-run table), maps rows to `Control` (private framework) + optional `RequirementMapping(source='manual')`; `ControlStatus.na_reason` column.
- WHERE: compliance.py (`GET/POST /compliance/import`, `POST /compliance/<id>/controls/add|edit|delete`, `POST /compliance/<id>/clone`), compliance.html "Import CSV" modal, compliance_detail.html control edit controls.
- Deps: none (mapping column needs G1). Effort S-M.

### G10. Control ownership as user + bulk actions (S)
- WHAT: owner is a real user (dropdown), department owner support, bulk assign/set N/A/set due date from framework page; "My controls" filter.
- HOW: add `owner_user_id` FK on ControlStatus; migrate by matching existing `owner` name to User.name; keep string for display fallback.
- WHERE: models.py, compliance_detail.html (checkbox column + bulk bar), `POST /compliance/<id>/controls/bulk`.
- Effort S. Deps none.

### G11. Dashboard parity polish (S-M)
- WHAT: widgets for "Tests failing", "Controls overdue", "My tasks", "Evidence expiring in 30 days", per-framework readiness bars with drill-down, framework/owner/date filters, per-framework trend selector, unified-vs-per-framework toggle, org-level roll-up for multi-entity (parent_org_id on Organization).
- HOW: extend `_dashboard_context` and `/api/dashboard/stats`; index ComplianceSnapshot by (org, date); add test pass-rate series to DashboardSnapshot (new columns `tests_passing`, `tests_failing`, `tasks_open`).
- WHERE: app/routes/main.py, app/services/snapshots.py, templates/dashboard.html.
- Deps: G2, G3, G5. Effort S-M.

### G12. Deepen the framework library (M, content-heavy)
- WHAT: expand ~17-control summaries to clause-complete sets for the top 15 frameworks (SOC 2 TSC all criteria, ISO 27001:2022 93 Annex A + clauses 4-10, HIPAA, PCI DSS v4 ~250 sub-requirements, GDPR articles, NIST CSF 2.0 subcategories ~106, NIST 800-53 Moderate ~287). 
- HOW: licensing-aware data work: NIST/HIPAA/GDPR/CSF are public domain/free; **ISO and PCI standard text is copyrighted** - ship own paraphrased control wording and clause numbers only (what Scrut/Vanta also do). Generate with AI + human review into the JSON; seed script already additive (extend to upsert new controls by (framework, code) rather than skip whole framework).
- WHERE: scripts/data/compliance_frameworks.json, scripts/seed_frameworks.py (upsert mode).
- Effort L (content), no dependencies; do after G1 so new controls get mapped.

### G13. Ticketing sync (S per provider) 
- Jira/Linear/GitHub Issues bi-directional for Task: `Task.external_ref`, webhook route `POST /webhooks/jira/<org_token>`. Needs customer credentials; Deps G2, G4. Effort M.

### Infeasible or limited without paid third-party access
- Scrut's 80+ maintained, vendor-vetted integrations and marketplace app listings; MDM/EDR partner APIs (CrowdStrike, Jamf, Intune need customer tenant + partner agreements for turnkey flows).
- Scrut's proprietary UCF mapping and test catalog (no public copy). Must be rebuilt from public crosswalks (NIST OLIR, SCF reference, CIS mappings) plus AI + manual curation.
- Licensed standard text (ISO/IEC, PCI SSC, AICPA TSC wording) cannot be reproduced; paraphrase only.
- Scrut Teammates-class AI beyond what the local AI dispatch (OpenCode/Cline) already gives; content-level evidence review needs OCR/text extraction (open-source Tesseract/pdfminer feasible, G-extra below).
- Real-time (24/7) tests: practical ceiling is scheduled runs (hourly/daily); webhooks per provider only where free.

### G14. Evidence content understanding (M, optional)
- Extract text from PDF/DOCX/XLSX/images (pdfminer, python-docx, openpyxl, Tesseract) at upload; store `Evidence.extracted_text`; feed to `ai_evidence_review._build_prompt` (replace metadata-only scope note); also check dates in doc against audit period. WHERE: app/services/evidence_extract.py, ai_evidence_review.py. Deps none.

---------------------------------------------------------------------------
## 5. Recommended build order

1. G5 due dates/recurrence/evidence expiry (S-M, quick win, feeds everything)
2. G7 control history + G10 owner-as-user (S, cheap, needed for exports)
3. G2 tasks/comments/notifications (M)
4. G1 unified control library (L, structural; start data curation in parallel with 1-3)
5. G3 test model + internal tests (L)
6. G6 gap analysis/readiness + G11 dashboard polish (M)
7. G9 CSV import/custom frameworks (S-M)
8. G8 audit package + auditor access (M)
9. G4 integrations (8-10 connectors) + G13 Jira (L, ongoing)
10. G12 library depth + G14 content-aware evidence AI (content-heavy, ongoing)

Projected parity after steps 1-8: ~85%; after 9-10: ~95% (remaining gap is connector breadth and Scrut's proprietary content).

## Sources
- https://www.scrut.io/faqs/general
- https://scrut.io/faq
- https://www.scrut.io/products/scrut-platform
- https://www.scrut.io/solutions/custom-frameworks
- https://www.scrut.io/hub/soc-2/soc-2-compliance-software
- https://www.scrut.io/
- https://www.trustradius.com/products/scrut-automation
- https://toolradar.com/tools/scrut-automation
- https://ismscopilot.hc.ferndesk.com/how-to-use-isms-copilot-with-scrut-617fk
- https://www.g2.com/compare/scrut-automation-vs-vanta
- https://www.rfp.wiki/legal-compliance/scrut-automation
