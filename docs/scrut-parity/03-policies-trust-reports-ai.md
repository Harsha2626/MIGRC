# Scrut parity, Section 3: Policies, Trust Center, Reports and AI

Research date 2026-11-04. Scrut sources are public pages only. Where a claim comes only from marketing or a search snippet, it is marked (M). Unverified items are marked (?).
MIGRC state comes from reading `app/routes/{policies,main,reports}.py`, `app/services/{pdf_reports,ai_*}.py` and the Policy*/NDAAcceptance models.

## 1. Scrut spec (public)

### 1.1 Policy builder and template library
- **Template count.** Scrut's own pages disagree, which suggests the library grows or the marketing is loose. The Compliance FAQ says 100+ editable templates mapped to SOC 2, HIPAA, ISO 27001 and GDPR. Other pages say 75+ and 140+. https://www.scrut.io/faqs/general , https://www.scrut.io/post/soc-2-compliance-policies
- **Framework library.** About 60 prebuilt frameworks, with a Unified Control Framework so one control maps across frameworks. https://www.getapp.com/security-software/a/scrut
- **Editor and import.** There is an in-built inline editor. Policies can be imported from PDF or DOCX. The Feb 2026 release notes add add, edit and remove of version entries in the inline editor. https://help.scrut.io/docs/february-2026
- **Content library.** It also includes training modules, video training with quizzes, and vendor questionnaires. https://platform.softwareone.com/product/scrut-platform/PCP-9523-4375
- **Help-center page titles (contents not retrieved).** "Understand Policy Approval Workflow", "Add Policy Approvers", "Set a Policy Review Cycle", "Manage Policy Versions".

### 1.2 Lifecycle, approvals, acknowledgement
- Policies are assigned to employees. Employees accept them in their own portal. Admins track who has acknowledged and can send reminders. Completion shows on the dashboard. (M, FAQ above)
- Policies have named approvers, a review cycle and versions. The detailed approval states are (?). The documented Under Review and Needs Revision loop is for mitigation tasks: https://help.scrut.io/docs/mitigation-task-approval-workflow

### 1.3 Trust Center (Trust Vault / Trust Portal)
Sources: https://www.scrut.io/platform/trust-center , https://help.scrut.io/docs/trust-vault-user-navigation , https://help.scrut.io/docs/add-custom-domain , https://help.scrut.io/docs/how-to-add-subprocessors , https://scrut.io/post/how-scrut-makes-multi-entity-trust-simpler-and-smarter
- **Sections.**
  - Org description.
  - Compliances: framework cards with a side panel showing the auditor and related documents.
  - Documents: searchable, with All, Public and Private tabs.
  - Controls: 13 predefined and customisable.
  - Sub-processors.
  - FAQs.
  - Updates: announcements and disclosures.
- **Gating.**
  - Private documents or frameworks show a lock and a "Get Access" button.
  - Admins approve or decline each request. Approved users get an emailed login link.
  - An NDA can be required on entry, with expiry dates and auto-approval rules.
  - Access can be set at entity, framework or control level.
- **Custom domain.** Available on paid plans. The customer adds a DNS record, then the Scrut CSM activates it.
- **Subprocessors.** Multiple entries, editable, linked to the Vendor module, and shown publicly.
- **Questionnaire deflection and automation.**
  - Scrut Teammates auto-fill prospect questionnaires from Vault documents, policies and an answer library.
  - CSV, portal and editable-PDF inputs are accepted.
  - A Chrome extension pushes answers into vendor portals.
  - Export is a ZIP with attachments.
- **Other.**
  - Multi-entity: one portal per entity under a unified domain.
  - Subscribe-to-updates for visitors.
  - "Trust impact tracking" with CRM linkage.
  - Live compliance status: (?) only "real-time" and "dynamic updates" are claimed. There is no named live-status widget.

### 1.4 AI ("Scrut Teammates" and Scrut MCP; no product called "Scrut Intelligence" was found)
Sources: https://www.scrut.io/products/scrut-teammates , https://help.scrut.io/docs/getting-started-with-scrut-teammates , https://www.scrut.io/post/meet-scrut-mcp
1. **Conversational GRC assistant.** Q&A over compliance data, summarising uploaded reports, and actions such as creating tickets and assigning owners.
2. **Remediation assistant.**
   - Prioritises failed tests.
   - Suggests fixes, including Terraform, Python and Node snippets.
   - Auto-creates tickets in Jira and similar tools.
3. **Vendor risk assistant.**
   - Estimates inherent risk.
   - Generates custom vendor questionnaires.
   - Analyses responses and suggests a risk score.
4. **Security questionnaire assistant.** Autofill with an editable answer library, citations and confidence flags (via MCP).
5. **Policy and evidence gap reviewer.**
   - Flags weak policies or evidence.
   - Maps policies to the controls they satisfy.
   - An Evidence Checker reviews manual evidence for completeness.
6. **Risk.** Create risks and suggest mitigations.
7. **Governance.** Opt-in and configurable. A human reviews questionnaire answers, evidence decisions and infrastructure changes.
- AI policy drafting from scratch is not confirmed (?).

### 1.5 Reports and exports
Public information is thin. Known items: framework readiness and audit-ready exports, auditor portal, questionnaire ZIP export, and risk and dashboard reports. A fuller list is (?). The help-center index at help.scrut.io/llms/help-center.txt (516 pages) was not parsed. It is a follow-up.

## 2. Parity table

| Capability | Scrut | MIGRC today | Status |
|---|---|---|---|
| Template library (75-140 mapped) | Yes | No library; `seed.py` has stub Policy rows (status "Not Uploaded", `requirement_text`) | Partial (roughly 10-20% of content) |
| Inline editor | Yes | `content` text field plus start-blank | Partial (no rich/WYSIWYG) |
| Import PDF/DOCX | Yes | Upload file or link URL, no text extraction | Partial |
| Framework mapping of policies | Yes | Single `framework` string plus control links | Partial |
| Status flow, approvers, sign-off | Yes | `STATUS_FLOW`, PolicyApproval, sign-off route | Has |
| Review cycle and reminders | Yes | `review_cycle_days`, `next_review`, notification type `policy_review_due` | Has |
| Versions and diff | Yes | PolicyVersion plus diff route | Has |
| Comments | Yes | PolicyComment | Has |
| Acknowledgement campaigns | Assign, remind, track | Per-employee ack route and count; no assignment campaign, due date, reminders, or per-version re-ack | Partial |
| Policy to employee portal | Yes | Ack route only | Partial |
| AI policy evidence evaluation | Gap reviewer | `PolicyEvaluation`, remediation, PDF | Has |
| AI policy drafting | (?) | No | Missing |
| Trust page, public | Yes | `/trust-center`, published policies, frameworks, score, badge, attestation PDF | Has (basic) |
| Document gating | Per-doc access requests, approval, email login | Single session NDA flag unlocks all downloads; no per-doc visibility, no approval | Partial |
| NDA with expiry or approval | Yes | NDAAcceptance row only; no expiry, no signed copy | Partial |
| Custom domain | Yes | No | Missing |
| Subprocessors | Yes, linked to Vendor | No public list | Missing |
| Trust FAQs, Updates, Controls sections, subscribe | Yes | No | Missing |
| Multi-entity or tenant portals | Yes | Pins first organization (`_trust_center_org`), not per-tenant slug | Missing |
| Branding | Yes | No | Missing |
| Access-request workflow | Yes | No | Missing |
| Trust analytics or CRM link | Yes | No | Missing |
| Questionnaire autofill | Yes | `ai_questionnaire.suggest_answers` with cites and confidence, from published policies and approved evidence | Partial (no answer library, no CSV/XLSX/PDF import, no export, no Q&A reuse) |
| Evidence review AI | Yes | `ai_evidence_review` | Has |
| Conversational assistant | Yes | No | Missing |
| Remediation or IaC fix suggestions | Yes | Partial: evaluation remediation fields, no fix suggestions or ticket push | Partial |
| AI risk suggestions | Yes | No | Missing |
| Vendor questionnaire generation and response analysis | Yes | Vendor assessment responses exist; no AI generation or analysis | Partial |
| Reports | Several | 3 PDF reports (dashboard, SOC 2 readiness, audit) plus policy and evaluation PDFs and CSV export | Partial |
| Scheduled or custom reports, CSV/XLSX of any module | Yes (?) | No | Missing |

**Honest parity: about 45%.** The count is 8 Has, 11 Partial and 11 Missing, with Partial counted at half and the "Has (basic)" trust page counted at 0.7. Policy mechanics are about 70%. The template library is about 15%. The Trust Center is about 25%. AI is about 45%. Reports are about 35%.

## 3. Plan to about 100% practical parity

### P1. Policy template library, 80+ items (L, highest value)
- **Legal strategy.**
  - Author original text only. Never copy Scrut, Vanta, Drata or SANS wording.
  - Use public control requirements only as a checklist of what a policy must address: ISO 27001 Annex A titles, SOC 2 TSC criteria IDs, HIPAA CFR sections, GDPR article numbers, PCI requirement numbers. Cite IDs only, not the standards' text.
  - Alternatively, license CC-BY sources such as the NIST SP 800-53 text, which is public domain US government work. Keep attribution in `source_note`.
  - Generate drafts with the local AI stack, using a prompt of the form "write an original policy from this outline". Then require human review before merging. Add a check that flags near-verbatim overlap (n-gram similarity) against any reference text kept in a scratch dir.
- **Architecture.**
  - Files: `app/data/policy_templates/<slug>.md`.
  - Each file has YAML front matter: `slug`, `title`, `category`, `version`, `frameworks: {iso27001: [A.5.1, ...], soc2: [CC1.1, ...], hipaa: [...], gdpr: [...], pci: [...]}`, `variables: [company_name, ciso_title, ...]`, `review_cycle_days`, `roles`.
  - Body is Markdown with `{{variables}}` placeholders and standard sections: Purpose, Scope, Roles, Policy statements, Exceptions, Enforcement, Review and history.
  - Model `PolicyTemplate` (slug unique, title, category, body_md, frameworks_json, variables_json, version, is_active). A loader runs at startup and upserts by slug and version.
  - `Policy.template_id` and `Policy.template_version` record provenance. Add a "template updated" banner with a diff to the policy.
- **Taxonomy, about 85 templates.**
  - Core security (about 25): InfoSec, Acceptable Use, Access Control, Password, Cryptography, Asset Mgmt, Data Classification, Retention and Disposal, Backup, Logging and Monitoring, Vulnerability and Patch, Network, Secure SDLC, Change Mgmt, Incident Response, BC/DR, Physical, Remote Work, BYOD, Vendor Mgmt, Risk Mgmt, HR Security, Security Awareness, Cloud Security, Endpoint.
  - Privacy (about 15): GDPR privacy, DPIA, DSAR, Data Breach Notification, Cookie, Records of Processing, DPO, Transfers, CCPA, and others.
  - HIPAA (about 10).
  - PCI (about 8).
  - ISO 27001 ISMS docs (about 12): scope, SoA procedure, internal audit, management review, and others.
  - SOC 2 specifics (about 6).
  - AI governance (about 5): AI Use, AI Risk, Model Mgmt, for ISO 42001 and NIST AI RMF.
  - Misc (about 5): Whistleblower, Code of Conduct, Anti-bribery, and others.
- **UI.**
  - A "Create from template" modal on `policies.html`: filter by framework or category, preview, fill variables, create a Draft.
  - A coverage matrix view showing which framework requirements have no policy.
  - New route `GET/POST /policies/templates` in `routes/policies.py`; new `templates/policy_templates.html`.
- **AI assist.** `ai_policy_draft.py` with two modes: tailor a template to an org profile (industry, size, stack, regions), and generate a template from an outline. Output JSON `{sections:[{heading,markdown}]}` through `run_compliance_agent`, with untrusted-input wrapping as in the existing services. The prompt rules are to use only the provided org facts, mark unknowns as `[TODO: ...]`, and avoid inventing certifications.
- **Authoring workflow.** Use a batch script `scripts/gen_policy_templates.py` that runs the AI over `outline.yaml` (title, frameworks, must-cover bullets), writes drafts to `app/data/policy_templates/_drafts/`, and a human then promotes them. The last step is a CI test that validates front matter, checks that every referenced control ID exists, and checks that each placeholder is declared. Effort is about 2 weeks of curation.

### P2. Trust Center v2 (L)
- **Data model.**
  - `TrustSettings` (org_id, slug, enabled, title, description_md, logo, brand_color, custom_domain, domain_verified, contact_email, show_score, nda_required, nda_text, nda_expiry_days).
  - `TrustDocument` (org_id, kind=policy/report/file/link, policy_id nullable, file, title, visibility=public/gated/hidden, framework_id, sort).
  - `TrustAccessRequest` (doc_id or null for all, email, name, company, reason, status pending/approved/denied, decided_by, token_hash, expires_at, ip).
  - Extend `NDAAcceptance` with org_id, version of NDA text, expires_at, signed PDF path, token.
  - `TrustSubprocessor` (org_id, vendor_id nullable, name, purpose, data_categories, location, website, show).
  - `TrustFAQ`, `TrustUpdate` (title, body, posted_at, notified).
  - `TrustSubscriber` (email, confirmed, token).
  - `TrustEvent` (type view/download/request/nda, doc_id, visitor email, ts) for analytics.
- **Routing.** Serve by `/trust/<slug>` and by Host header for custom domains. A before_request resolver maps Host to org. Replace `_trust_center_org`'s "first org" with this resolver. Documentation for custom domains is CNAME to the MIGRC host, with a TXT token verified by a DNS lookup, and Caddy on-demand TLS with an `ask` endpoint at `/_domain-ok`.
- **Access flow.** A gated document shows a lock and "Request access". The visitor submits the form; an admin gets a notification and emails; the admin approves, denies, or auto-approves by email-domain rules or if the NDA is signed. Approval generates a signed magic-link token with expiry that is stored in a session. Downloads are checked per document against the token, replacing the session boolean. Every download is logged and watermarked: for PDFs, a footer with the visitor email and date through the existing `pdf_reports` FPDF code.
- **Live status.** Per-framework tiles with the pass percentage, "last updated", a per-control category pass summary (all computed from existing Framework data), and an optional public uptime or status URL.
- **Admin UI.** A `settings/trust` page with tabs: Branding, Documents, Access requests, NDA, Subprocessors, FAQ, Updates, Analytics, Domain.
- **Questionnaire deflection.** A search box over the public FAQ and answer library, plus "Ask a question". Visitors can upload a questionnaire (gated by email) which creates an inbound `Questionnaire` job for admins (see P3).
- **Controls section.** A public list of 13 or so control summaries (encryption, MFA, backups, and so on) with Implemented/Planned toggles, linked to real Control pass state.
- **Security.** Rate-limit the public forms, add CSRF to the public POSTs, hash tokens, protect against open redirect on `external` links, and never expose draft or unpublished policies.
- **Subscribe.** A confirmed-email list notified on new updates or documents, through the existing mail or notification layer.

### P3. Questionnaire automation v2 (M-L)
- **New models.**
  - `AnswerLibraryEntry` (org_id, question_text, answer_md, tags, source citations, owner, last_verified, embedding or keyword index).
  - `InboundQuestionnaire` (org_id, customer, source file, status, due date) with `InboundQuestion` rows (question, answer, confidence, cites, approved_by, library_entry_id).
- **Services.**
  - Parsers for CSV, XLSX (openpyxl) and DOCX or PDF question extraction.
  - Matching in two steps: first fuzzy match on the library with rapidfuzz or TF-IDF, with reuse above a threshold; then AI for the rest through `ai_questionnaire._build_prompt`. Reuse the existing parse and cite validation, and add the library as a context block `[L<id>]`.
  - Export fills the original XLSX or CSV and bundles evidence into a ZIP.
  - An approved answer is saved to the library (the learning loop).
- **Routes.** `/questionnaires/inbound`, `/inbound/<id>`, `/answer/<qid>/approve`, `/export`.
- **Prompt delta.** "Answer strictly from the provided sources. If the sources are insufficient, output answer = '' and confidence 0. Give a short answer plus a yes/no/partial field." Add `answer_type` to the JSON schema.
- **Chrome extension.** Skip. Offer the copy-friendly view instead.

### P4. Acknowledgement campaigns (M, high value, quick win)
- `PolicyAckCampaign` (policy_id, version, due_date, audience_filter, created_by, reminder_days_json) and `PolicyAckAssignment` (campaign_id, employee_id, status, notified_at, acked_at).
- Add `version` to `PolicyAcknowledgement`, and require re-ack on a major version bump.
- Reminder job in the existing `scheduled-jobs` runner: send at T-7, T-1 and overdue, using `Notification` and email.
- Employee "My policies" page with an accept button and read-time tracking.
- Campaign detail page with progress, per-person status, a "remind all" button and CSV export, plus a dashboard widget.
- Audience filters by department, entity or role, and auto-assign on new employee onboarding.

### P5. AI assistant and extra AI features (M each)
All of these go through `ai_dispatch.run_compliance_agent(prompt_text, parse_fn, log_tag)` and are advisory.
- **Policy draft and tailor.** See P1 (M).
- **Policy to control mapping.** Input is the policy text plus a control list (ids and titles), output is `[{control_id, coverage: full|partial|none, quote}]`. The user confirms links through the existing `policy_controls` table (S-M).
- **Risk suggestions.** Input is an org profile, assets and vendors; output is risks with likelihood and impact, plus mitigations. It creates risk drafts with `source=ai` (M).
- **Q&A assistant.** RAG over policies, controls, test results and evidence metadata. Start with keyword retrieval (SQLite FTS or whoosh) and put the top-k snippets in the prompt with `untrusted()` wrapping. Chat UI with a side drawer. Read-only tools only at first; action creation (ticket, assign owner) comes later behind a confirm step (L).
- **Remediation suggestion.** For a failed test, return fix steps plus an optional Terraform or CLI snippet, marked "review before applying". It is displayed only, never executed (M).
- **Vendor AI.** Generate a questionnaire from vendor type and data access; analyse responses and suggest a risk score and flags. Reuses `VendorAssessment*` (M).
- **Guardrails.** An org-level AI toggle (off by default, as Scrut does it), an audit log of AI calls, and a visible "AI-generated, needs human approval" badge. Keep the current gated-model fallback logic.

### P6. Reports and exports (M)
- **Report catalogue page.**
  - Reports: framework readiness for any framework (generalise `build_soc2_readiness_pdf`), control status, test results, policy status and ack, risk register, vendor risk, access review, training completion, evidence index, audit-ready package (ZIP of evidence plus index CSV).
  - Output formats: PDF, CSV and XLSX.
  - Add a shared `report_registry` of dicts (key, title, builder, formats, filters) so that `reports.html` is data-driven.
- **Scheduled reports.** `ScheduledReport` (org_id, report_key, cron/frequency, recipients, format, last_run) run by the daily-jobs runner and emailed.
- **Branding.** Org logo and name in PDFs. Remove the hard-coded 'Midevops Services Pvt Ltd' default in `build_trust_certificate_pdf`.
- **Report history.** `ReportRun` with the generated file.

### P7. Smaller items (S)
- Rich text editor (Quill or TipTap via cdnjs) with Markdown or HTML storage, plus DOCX/PDF text extraction on import (python-docx, pypdf) (S-M).
- Policy `frameworks` many-to-many via a mapping table, instead of a single string (S).
- NDA expiry and a signed-PDF copy emailed to the visitor (S).

## 4. Priority order (value over effort)
1. P4 Acknowledgement campaigns, M.
2. P1 Policy template library plus create-from-template, L. It is the biggest visible gap.
3. P2 Trust Center v2: slug and org resolver, per-document gating and access requests, subprocessors, FAQ and updates, then custom domain and analytics.
4. P3 Questionnaire answer library and import/export.
5. P6 Report registry, CSV/XLSX, scheduling.
6. P5 AI mapping, draft, Q&A, remediation and risk suggestions.
7. P7 Editor and import.

Rough total is 10-14 weeks for one developer. Reaching about 85% takes P1 to P4. The remainder is P5 to P7 polish. Features that need Scrut's infrastructure, namely the Chrome extension, CRM-linked trust impact, and CSM-assisted domain activation, are better replaced by cheaper equivalents (copy view, built-in analytics, self-serve DNS verification), so practical parity is near 95%.

## 5. Caveats
- Scrut's public pages give inconsistent template counts (75, 100 and 140), and policy approval and ack details were not directly retrievable.
- Report catalogue and NDA details are thinly documented publicly.
- All AI claims are vendor marketing.
- Follow-up: parse https://help.scrut.io/llms/help-center.txt for the full page list.
