# Section 4: Risk Management, Vendor Risk (TPRM) and Incidents - Scrut parity

Research basis: PUBLIC sources only (scrut.io product pages, help.scrut.io docs, press, search snippets). No Scrut application/API hosts were touched. Where the public docs are silent, this is stated ("not public") rather than guessed. Date: 2026-11-04.

## 1. Scrut's spec (what is publicly documented)

### 1.1 Risk register
Sources: https://www.scrut.io/products/risk-management , https://help.scrut.io/docs/understanding-risk-register , https://help.scrut.io/docs/quick-start-guide-risk-management , https://help.scrut.io/docs/configuring-custom-risk-score-formula , https://help.scrut.io/docs/risk-assessment-1 , https://www.helpnetsecurity.com/2022/08/03/scrut-automation-risk-management

- Creation: Risk Discovery tab (pre-built library of common risks, bulk add), manual, bulk import XLSX/CSV, auto-created from other modules (failing tests, cloud, assets, vendors, vulnerabilities, audit findings). AI-suggested risks (policy drift, cloud tests, history).
- Register: custom fields, custom categories, auto-generated Risk IDs with custom prefix, custom table layout/columns, filters (assignee, department, category, entities, source type, treatment strategy, type, major/minor, recurrence, dates), status cards.
- Lifecycle: Open -> Assessed -> Treatment in Progress -> Treated -> Monitor / Closed. Optional approval workflow adds Pending Approval and Needs Revision. Monitor is automatic when Review Date passes; Close is manual with approvals.
- Scoring: fully configurable engine (Growth/Scale plans). Risk FACTORS (likelihood, impact, control effectiveness, etc.) tagged Inherent or Residual, each with severity ranges (named bands, numeric ranges, colors). Risk SCORES are formulas with 4 methods: Maximum, Minimum, Conditional (IF/ELSE), Custom (`(Impact*Likelihood)/5`, + - * / ^). Rounding options (standard/up/down). Separate formulas for inherent and residual.
- Treatment: Accept / Avoid / Transfer / Mitigate. Mitigate/Transfer need mitigation tasks (owner, deadline, auto reminders) and residual risk; Accept needs residual risk; Avoid neither. Mitigation tasks must close before residual is entered. Controls linked to risks (by framework or individually) and carried into tasks.
- Reporting: PDF risk report (heatmap configurable, inherent vs residual comparison, filter by status/entity, emailed), CSV export, dashboard (concentration, posture trend), audit trail of status changes/score edits/settings.
- Risk appetite/tolerance: NOT publicly documented (no page found). Treat as unknown; likely absent or thin.
- Risk assessment campaigns: not publicly documented; "assessment" = per-risk inherent scoring step.

### 1.2 Vendor management / TPRM
Sources: https://www.scrut.io/products/vendor-risk , https://help.scrut.io/docs/steps-to-complete-vendor-risk-assessment , https://help.scrut.io/docs/ai-enhanced-vendor-assessment , https://help.scrut.io/docs/understanding-vendor-details-page , https://help.scrut.io/docs/evaluating-vendor-questionnaire , https://help.scrut.io/docs/quick-start-guide-vendor-management

- Inventory/discovery: SSO-based discovery (Google Workspace, Azure AD), cloud-infra scan for third-party apps, CSV bulk upload, prospective vendors assessed pre-onboarding, customizable intake forms.
- Profile: service description, URL, assignee, category, Vendor Tier (1/2/3), Inherent Risk, Residual Risk (Critical/High/Medium/Low), entities, sub-processor flag, recurrence (annual/bi-annual/quarterly/monthly/never/custom), next assessment, multiple POCs, custom fields. Tabs: Overview, Questionnaires, Mitigation Tasks, Documents, Audit Logs. Widgets: avg risk score by domain, questionnaire status, mitigation status. Assessment-progress timeline Discovered -> Final Assessment.
- AI inherent-risk classification (Scrut Teammates): from data accessed, customer impact, managed-by; "Complete Service Disruption" dependency forces Critical; reasoning viewable; manual override.
- Questionnaires: library, org templates, custom, or AI-generated from CAIQ tailored to vendor profile and your frameworks (SOC2/PCI/GDPR/HIPAA); irrelevant questions pruned; per-question Domain, Weightage, attachment requirement. Document-based autofill from vendor Documents tab before sending (only unanswered go to vendor).
- Vendor portal: email to POC (must have POC) with link to Scrut Vendor Portal where vendor LOGS IN, handles multiple assessments, gets live status; AI real-time answer-quality prompts (vague answers).
- Review: per-question accept / flag / comment / create mitigation task / log risk; AI "Start Check" flags risky/vague answers with recommended mitigations (add to risk register, task, or ignore); mark Assessed locks vendor edits; scorecard; PDF report (details, summary, scores, responses, tasks, risks).
- Scoring: domain + weightage based; exact formula not public.
- Statuses: questionnaire Created/Sent/Submitted/Assessed/Overdue; tasks Overdue/Not Due/Closed; vendor "Needs Reassessment" on due date, reviewer notified 1 week ahead.
- Monitoring: AI scans online sources for breach/threat news on vendors (marketing claim). Reviewers rate depth below dedicated TPRM tools (RFP.wiki, G2 vs UpGuard).
- SOC2 report AI review: not explicitly documented; closest is "AI identifies risks from uploaded documents".
- Offboarding: Archive on profile with mandatory justification; unarchive possible.

### 1.3 Incident management
Sources: https://www.scrut.io/integrations/servicenow , PagerDuty/Freshservice/ServiceDesk Plus help pages (help.scrut.io/docs/integrating-freshservice etc.)
- No native incident-management module is publicly documented. Scrut ingests incident data from PagerDuty, ServiceNow, Freshservice, ServiceDesk Plus as EVIDENCE for incident-response controls and can open tickets for findings. MIGRC's native incident module therefore already EXCEEDS Scrut publicly; the parity gap is only the integration/ticketing evidence side (covered in the integrations section).

## 2. MIGRC current state (read from code)
- Risk (models.py:381): qualitative likelihood/impact strings, fixed 1-5 map (RISK_LEVEL_SCORES) score = L*I hard-coded; residual L/I/score fields; owner is free text; one treatment strategy string + RiskTreatment tasks (owner, department, deadline, 5-status workflow incl. Pending Approval/Needs Revision) + TreatmentMilestone; mitigating_controls M2M; 15-item RISK_CATALOG; csv export; JS risk matrix (`/api/risks/matrix` uses only 3 likelihood x 4 impact buckets - inconsistent with 5-level scale); notify_risk_escalated; incident<->risk link. Risk status is a free string (default Open); no review date, appetite, history, custom fields, risk IDs, asset/vendor links, approval gate.
- Vendor (models.py:801): name, category, status, website, contact, last/next assessment (fixed 180 days), compliance JSON; Evidence-backed documents; no tier, inherent/residual, owner, data classification, criticality, POCs, archive.
- Questionnaire: template + free-text questions only (no types, domain, weight, required, evidence attachment, branching). VendorAssessment: Sent/In Progress/Completed, verdict Pass/Fail/Needs Follow-up, reviewer_notes. Responses are filled IN by an internal user (`respond` route is login-required): "send" only creates a DB row - NOTHING is emailed and vendor cannot answer. No scoring, no per-answer review, no mitigation tasks from answers.
- AI: ai_questionnaire.suggest_answers answers OUR side of questionnaires (inbound security questionnaire style) from published policies/evidence via run_compliance_agent, with citation validation and untrusted() wrapping (good pattern to reuse). No AI vendor-response review, SOC2 review, or tiering.
- Incident: strong native module (severity, 6-stage lifecycle, timeline, owner, controls and risks link, PIR, CSV, notifications to owner). Missing: vendor link, SLA/notification clocks, regulatory breach notification tracking, severity-based assignment, assets as relations (free text), tasks, templates/playbooks.

## 3. Parity table

| Capability | Scrut | MIGRC | Status |
|---|---|---|---|
| Risk library / discovery | Yes, bulk add | 15-item catalog, single add | Partial |
| Manual add, CSV export | Yes | Yes | Has |
| Bulk import XLSX/CSV | Yes | No | Missing |
| Auto-create risks from tests/cloud/assets/vendor/audit | Yes | Only manual/"discovery add" | Missing |
| AI risk suggestions | Yes | No | Missing |
| Custom fields/categories/risk-ID prefix | Yes | Fixed categories, no ID | Missing |
| Configurable scoring (factors, 4 methods, bands) | Yes | Hard-coded L*I | Missing |
| Inherent vs residual | Yes | L/I + residual L/I | Partial |
| Lifecycle statuses incl. Assessed/Monitor/Treated/Closed | Yes | free string Open/etc | Partial |
| Treatment Accept/Avoid/Transfer/Mitigate + rules | Yes | strategy string, no enforcement | Partial |
| Mitigation tasks owner/deadline, milestones | Yes | Yes (+milestones) | Has |
| Task reminders | Yes | no scheduled reminders seen | Missing |
| Approval workflow | Yes | task-level statuses only | Partial |
| Review date / auto Monitor | Yes | No | Missing |
| Control linking | Yes | Yes | Has |
| Asset/vendor/entity linking | Yes | No (incidents only link risks) | Missing |
| Heatmap | Yes (configurable, PDF) | JS matrix, fixed 3x4 | Partial |
| PDF risk report, inherent vs residual | Yes | CSV only (pdf_reports exists, not for risk) | Missing |
| Dashboard trends / audit trail | Yes | activity log only, no score history | Partial |
| Risk appetite / tolerance | Not public | No | Missing (Scrut unknown; do anyway, differentiator) |
| Vendor inventory, CRUD, CSV export | Yes | Yes | Has |
| Vendor discovery (SSO / CSV) | Yes | No | Missing |
| Vendor tier, inherent/residual, criticality | Yes | No | Missing |
| Vendor POCs / assignee / sub-processor / custom fields | Yes | single contact | Partial |
| Questionnaire templates | Yes + library + AI CAIQ | Basic text list | Partial |
| Domain/weight/attachments per question | Yes | No | Missing |
| Send to vendor + external portal | Yes (login portal) | No - internal fill only | Missing (largest gap) |
| AI answer-quality check for vendors | Yes | No | Missing |
| AI autofill from vendor docs | Yes | Reverse direction only | Missing |
| Response review (accept/flag/task/risk) | Yes | verdict + notes | Partial |
| AI response risk flagging | Yes | No | Missing |
| Vendor risk score by domain | Yes | No | Missing |
| PDF assessment report | Yes | No | Missing |
| Reassessment recurrence + reminder | Yes (custom recurrence, 1 wk notice) | Fixed 180 days, no reminder, no status | Partial |
| SOC2 report intake/AI review | Not explicit | Doc upload only | Missing |
| Vendor offboarding/archive w/ justification | Yes | Hard delete | Partial |
| Vendor monitoring (breach news) | Claimed | No | Missing (low value) |
| Native incident mgmt | No (integrations only) | Yes | Has (ahead) |
| Incident ticketing/PagerDuty evidence | Yes | No | Missing (integrations section) |

Count (35 rows excluding incident ahead-rows weighting): Has 6, Partial 11, Missing 16 (+2 incident rows). Weighted (Has=1, Partial=0.5) = (6+5.5)/33 = ~35%. Honest parity: Risk register ~45%, Vendor/TPRM ~20% (no external flow), Incidents ~100% of Scrut's public scope. Overall Section 4: ~35%.

## 4. Plan (WHAT / HOW / WHERE)

Conventions: org-scoped queries (`organization_id`), `require_permission('write')`, `log_activity`, alembic/idempotent migration pattern as used elsewhere in repo; AI only via `ai_dispatch.run_compliance_agent` + `untrusted()` + parse validation (pattern in ai_questionnaire.py).

### P1. External vendor questionnaire portal (L) - highest value
WHAT: vendor POC receives emailed link, answers without a MIGRC account, uploads evidence, submits; reviewer then scores. Scrut uses a login portal; tokenized link is lighter and is the right self-hosted choice (optional OTP upgrade).
HOW / DATA MODEL:
- `VendorPOC(id, vendor_id, organization_id, name, email, is_primary)`.
- Extend `VendorAssessment`: `due_date`, `sent_at`, `submitted_at`, `assessed_at`, `assigned_reviewer_id`, `status` enum Created/Sent/In Progress/Submitted/Assessed/Overdue/Cancelled, `score`, `risk_level`, `poc_id`, `locked` bool.
- `VendorAssessmentAccess(id, assessment_id, token_hash CHAR(64) unique, poc_id, expires_at, revoked_at, last_used_at, use_count, otp_hash NULL, otp_expires NULL, failed_attempts, created_at)`. Store only SHA-256 of a `secrets.token_urlsafe(32)`; raw token only in the email. Compare with hash lookup (constant-time via unique index on hash of high-entropy token).
- Extend `QuestionnaireQuestion`: `question_type` (text/yes_no/single/multi/file/date), `options` JSON, `required`, `domain`, `weight` (1-5), `evidence_required`, `risk_if_answer` JSON (e.g. {"No": "high"}), `section`.
- `VendorAssessmentResponse` add: `answer_value`, `file_evidence_id`, `reviewer_status` (accepted/flagged/pending), `reviewer_comment`, `score`, `ai_flag` JSON, `updated_by_poc_id`, `updated_at`.
WHERE:
- New blueprint `app/routes/vendor_portal.py`, prefix `/vp/<token>` with NO login: GET form, POST save-draft (autosave), POST file upload, POST submit. Add to CSRF handling (token in URL authorizes; keep CSRF on forms using a per-session csrf token, do not blanket exempt).
- `send_assessment` route: require vendor POC, generate access, send email via `app/services/mail.py` (prefilled editable subject/body), set status Sent, `resend`, `revoke`, `extend` routes.
- Templates: `vendor_portal.html` (standalone minimal layout, no org navigation, org name/logo only), `vendor_portal_done.html`, `vendor_portal_expired.html`; update `vendor_assessment.html` into reviewer view (per-answer accept/flag/comment/create task/log risk).
SECURITY: 32-byte random token; hash at rest; default 30-day expiry, configurable; single assessment scope (token cannot read other data; every query keyed by access.assessment_id); revoked/expired/submitted-and-locked returns generic 404/410 identical page to avoid enumeration; rate limit per IP and per token (Flask-Limiter or simple DB counter), lockout after N failed OTPs; optional email OTP (6 digits, 10 min, hashed) when `org.vendor_portal_otp` on; `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, `X-Robots-Tag: noindex`, CSP strict, no third-party assets (token must not leak via Referer); file uploads: size cap, extension+magic allow-list, random storage names, stored in org-scoped evidence dir, served only to authenticated reviewers via download route, AV hook if available; sanitize all answers (Jinja autoescape; never mark safe); log access (IP hash, UA) to ActivityLog/`VendorAssessmentAccess.last_used_at`; after Submit set `locked`, vendor cannot edit; reviewer can "reopen" which mints a new token and invalidates the old; never include secrets in emails except the link; TLS-only link generation using configured BASE_URL (not Host header, prevents host-header poisoning).
NOTIFICATIONS: email to POC on send/reminder (T-7, T-1, overdue), in-app + email to reviewer on Submitted and on Overdue. Needs a scheduled job (see P5).

### P2. Vendor tiering, inherent/residual risk and automated rules (M)
WHAT: tier + inherent + residual + criticality on Vendor; rule-based automation, AI as advisory.
DATA: Vendor add `tier` (1-3), `inherent_risk`, `residual_risk`, `criticality`, `data_classification` (None/Internal/Confidential/Regulated), `data_types` JSON (PII, PHI, PCI, credentials), `access_level` (none/read/write/admin/network), `integration_type`, `customer_facing` bool, `dependency_level` (Replaceable / Degraded / Complete Disruption), `sub_processor` bool, `owner_id` (FK users, replaces free text), `relationship_start`, `contract_end`, `archived_at`, `archive_reason`, `intake_json`.
RULES (service `app/services/vendor_tiering.py`, pure and unit-testable): additive points: data class (Regulated 4, Confidential 3, Internal 1), PII/PHI/PCI +2 each, access admin +3 / write +2, customer-facing +2, dependency Complete Disruption => force Critical (Scrut parity), sub-processor +1, no SOC2/ISO cert on file +1. Map score to inherent Low/Medium/High/Critical then tier: Critical->Tier 1, High->Tier 1/2, Medium->Tier 2, Low->Tier 3. Rules table `VendorTieringRule` (org-editable thresholds) later. Residual = inherent adjusted by assessment score (e.g. score >=80% drops one level, <50% keeps/raises) and open mitigation tasks. Tier drives: questionnaire template default (Tier1 full, Tier3 lite), reassessment recurrence (T1 annual->quarterly options, T2 annual, T3 24 months), and required docs.
AI (optional button "Suggest risk level"): `run_compliance_agent` prompt wrapped in `untrusted()` with the intake answers; parse_fn validates level in the enum and returns reasoning; never auto-applies, shows reasoning like Scrut's Info icon; manual override stored with `inherent_risk_source` (rule/ai/manual).
WHERE: models.py, `vendors.py` edit/add routes, `vendors.html` columns/filters, `vendor_detail.html` profile card, intake form (new `vendor_intake` modal).

### P3. Configurable risk scoring engine (M-L)
Options:
 A (recommended default): configurable qualitative matrix - org picks 3x3/4x4/5x5, names each level, defines band thresholds and colors, heatmap derived from it. Score = L*I default.
 B: Scrut-style factor/formula engine - `RiskFactor(org, name, kind inherent|residual, ranges JSON)` and `RiskScoreFormula(org, kind, method max|min|conditional|custom, expr, rounding, ranges)`; evaluate with a SAFE parser (ast whitelist of + - * / ^ parentheses and names; no eval) and conditional via small if/else JSON structure. Cap expr length, depth.
 C: quantitative FAIR-lite: annualized loss expectancy = frequency (events/yr) x loss magnitude (min/likely/max, PERT or simple Monte Carlo in service), stored as `ale_min/likely/max`, shown in currency alongside qualitative score; compare to appetite in dollars.
 Ship A first with B hooks (formula stored per org), C later as optional fields.
DATA: `RiskScoringConfig(org_id, matrix_size, likelihood_labels JSON, impact_labels JSON, bands JSON, method, formula JSON)`; Risk add numeric `likelihood_value`, `impact_value`, `residual_*_value`, keep old strings for compat with backfill migration mapping Negligible..Critical to 1-5; `score_calculated_at`.
FIX NOW: `/api/risks/matrix` ignores 5-level scale (only High/Medium/Low columns) - rewrite to read config and count by value for inherent AND residual.
WHERE: new `app/services/risk_scoring.py` (compute, band, safe-eval), settings page `risk_settings.html`, `risks.py` add/edit use service, `risks.html` heatmap rendering from config, toggle inherent/residual.

### P4. Risk lifecycle, treatment rules, appetite, review (M)
- `Risk` add: `risk_code` (org prefix + sequence, table `OrgSequence` or computed), `status` enum Open/Assessed/Treatment in Progress/Pending Approval/Needs Revision/Treated/Monitor/Closed with transition validator `risk_workflow.py`, `treatment_strategy` enum Accept/Avoid/Transfer/Mitigate (+ rule enforcement: Mitigate/Transfer require tasks done + residual; Accept requires residual and justification; Avoid none), `review_date`, `owner_id` FK users, `approver_id`, `approved_at`, `source_type/source_id` (test, vendor, asset, incident, finding, manual), `asset_ids`/`vendor_id` links (M2M `risk_assets`, `risk_vendors`), `custom` JSON, `closed_reason`.
- `RiskHistory(risk_id, user_id, field, old, new, at)` for audit/trend and inherent-vs-residual over time; `RiskSnapshot` monthly (see services/snapshots.py) for posture trend chart.
- Risk appetite: `RiskAppetite(org_id, category NULL, max_residual_score, tolerance_band, statement)`; flag risks above appetite (badge on register, filter, dashboard widget "Outside appetite"), require approval/justification to Accept above appetite, notify owner. Differentiator vs Scrut (not public there).
- Automatic transition to Monitor when review_date passes (daily job), reminders for tasks due T-7/T-1/overdue.
- Risk assessment campaigns (M, later): `RiskAssessmentCampaign(org, name, due, scope filter)` + `RiskAssessmentItem(campaign, risk, assessor, status)`; assign owners to re-score residual by deadline; uses same notification job.
- Approval: reuse treatment status transitions; add approver role check.
WHERE: models.py, `risks.py` (new routes `/risks/<id>/status`, `/risks/<id>/assess`, `/risks/appetite`), `risk_detail.html` (workflow stepper, history tab, links), `risks.html` (register columns/filters/status cards).

### P5. Scheduler and notifications (S-M, prerequisite for P1/P2/P4)
WHAT: daily job (cron/CLI `flask daily-jobs`, repo already ignores a daily-jobs log so a runner exists - reuse) that: marks vendor assessments Overdue, sends portal reminders, sets vendors Needs Reassessment and notifies reviewer 7 days prior, moves risks to Monitor, reminds risk tasks and treatment deadlines. WHERE: `app/services/notifications.py` add `notify_vendor_reassessment`, `notify_assessment_submitted`, `notify_task_due`; use `dedupe_key` param already supported. Vendor `recurrence` enum replacing hard-coded VENDOR_REASSESSMENT_DAYS.

### P6. Vendor assessment review, scoring, report (M)
- Scoring service `vendor_scoring.py`: per answer score (0-1) from `risk_if_answer` rules or reviewer 0/0.5/1; domain score = weighted average; overall = weighted over domains; map to risk level; `Vendor.residual_risk` suggestion; heatmap-able "average risk score by domain" chart on vendor_detail.
- Reviewer actions per answer: accept, flag, comment, create `VendorMitigationTask` (new table: vendor_id, assessment_id, question_id, title, owner, due, status), log risk (creates Risk with source_type=vendor, linked vendor).
- Mark Assessed locks portal; PDF report via `pdf_reports.py` (details, summary, scores, responses, tasks, risks).
- `VendorMitigationTask` also shows on vendor_detail tab and in dashboard.

### P7. AI for vendor workflows via run_compliance_agent (M)
All follow ai_questionnaire.py template (org-scoped context, `untrusted()`, strict JSON schema, id-validation, advisory-only, fail-open):
1. `ai_vendor_questionnaire.generate_questionnaire(vendor, frameworks)` -> proposes questions with domain/weight from CAIQ-like domains tailored by tier and data types; human reviews before saving as template.
2. `ai_vendor_review.review_responses(assessment)` -> per answer flag {question_id, severity, justification, suggested_mitigation}; validated question ids; reviewer chooses add-to-register / task / ignore.
3. `ai_vendor_docs.review_soc2(evidence)` -> extract text from uploaded PDF (pdf text extraction locally; truncate), ask for: report type (I/II), period, auditor opinion (unqualified/qualified), exceptions noted, scope/trust criteria covered, CUECs, subservice carve-outs, report age vs 12 months. Output JSON stored on Evidence/`VendorDocumentReview(vendor_id, evidence_id, extracted JSON, reviewed_by, reviewed_at)`; auto-fill vendor `compliance` badges and expiry date -> reminder. Mandatory human confirm; wrap document text with `untrusted()` (reports are attacker-controlled input).
4. Portal answer-quality nudges: optional, synchronous call per answer on blur capped by rate limit; start with post-submit check only to avoid latency/abuse of a public endpoint (public endpoint triggering LLM calls = cost/DoS vector; gate behind token validity and per-token quota).
5. Risk AI: `ai_risk_suggest` - from failing tests/policy gaps propose risks with cited ids; "improve risk statement" and suggest treatment. Same pattern.
6. Autofill of vendor questionnaire from vendor Documents (reuse suggest_answers concept pointed at vendor evidence instead of our own).

### P8. Library, import and cross-module risk creation (S-M)
- Expand RISK_CATALOG to ~100-150 entries, move to JSON seed `app/data/risk_library.json` with category, default L/I, suggested controls (map by control ref), tags; bulk-select add (checkbox) in discovery UI; mark in-register.
- Bulk import CSV/XLSX (`/risks/import`, template download, dry-run validation, per-row errors, openpyxl).
- "Create risk" actions from: failing control test, asset detail, vendor detail, audit finding, incident (use `source_type`). Dedupe by source.
- Custom categories table `RiskCategory(org, name)`, custom fields JSON definition (`CustomFieldDef(org, entity, key, label, type)`).

### P9. Vendor inventory polish (S-M)
- Multiple POCs (VendorPOC), assignee, sub-processor, contract dates, CSV import of vendors, archive with mandatory reason (replace hard delete as default; keep delete for admin), unarchive, filter by tier/risk/status, "Needs Reassessment" status, offboarding checklist (revoke access, retrieve/delete data, final DPA/termination confirmation, close linked risks) as `VendorOffboardingTask` rows generated on archive.
- Discovery: import vendors from existing Google/Azure SSO integration app lists if integrations section implements OAuth app inventory (dependency); otherwise CSV only.
- Skip vendor breach-news monitoring (marketing claim, high cost, no data source); optionally later add RSS/HIBP-domain check.

### P10. Reporting (M)
- PDF risk report (`pdf_reports.py`): register summary, heatmap (inherent and residual side by side), top risks, treatment status, outside-appetite list, filters by status/category; email option via mail service.
- Dashboard widgets: risk by status, posture trend (RiskSnapshot), vendors by tier/risk, overdue assessments, open vendor tasks.
- Vendor PDF in P6.

### P11. Incident enhancements (S-M, beyond Scrut parity, low priority)
Link vendor (`incident_vendors` M2M) so Vendor/Third Party incidents raise vendor reassessment and risk; asset relation instead of free text; response-clock fields (`detected_at`, `acknowledged_at`, `contained_at`) and MTTA/MTTR metrics; regulatory notification tracker (GDPR 72h deadline countdown); create risk from incident (source_type); PagerDuty/ServiceNow ingestion (belongs in integrations section).

## 5. Effort and ordering by value

| # | Item | Effort | Value | Depends |
|---|---|---|---|---|
| 1 | P5 scheduler/notifications | S-M | High (enabler) | none |
| 2 | P1 external vendor portal + send/email + POC | L | Highest (biggest gap, headline Scrut feature) | P5 |
| 3 | P6 review/scoring/mitigation tasks/PDF | M | High | P1 |
| 4 | P2 vendor tier/inherent/residual rules | M | High | none |
| 5 | P3 scoring engine (A first) + matrix fix | M-L | High | none |
| 6 | P4 risk lifecycle/treatment rules/appetite/history | M | High | P3 |
| 7 | P7 AI (questionnaire gen, response review, SOC2 review) | M | High (differentiator, low cost since pattern exists) | P1, P6 |
| 8 | P8 library + import + cross-module creation | S-M | Med-High | P4 |
| 9 | P9 vendor inventory polish/offboarding | S-M | Medium | P2 |
| 10 | P10 reporting/dashboard | M | Medium | P3, P4 |
| 11 | Campaigns, quantitative (FAIR-lite) scoring | M | Medium-Low | P3, P4 |
| 12 | P11 incident extras | S-M | Low (already ahead) | none |

Quick wins (S, do first regardless): fix `/api/risks/matrix` 5-level bug; validated status/treatment enums; vendor `recurrence` instead of fixed 180 days; archive instead of delete; add `owner_id`/`review_date` to Risk.

Testing notes: unit tests for scoring safe-evaluator (reject names/attributes/calls), tiering rules, token lifecycle (expired, revoked, replay after submit, cross-assessment access, brute-force), and org scoping on every new route.
