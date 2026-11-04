# MIGRC vs Scrut — Master Parity Roadmap

Built from six public-source research reports (this folder). Scrut was studied from public pages only
(marketing, FAQ, help-center fragments, reviews). Items Scrut does not publish are marked UNKNOWN in the
section reports, not guessed.

## Parity scorecard (honest, value-weighted)

| # | Section | Parity | Biggest gap |
|---|---|---|---|
| 1 | Compliance core + dashboard | ~31% | No unified cross-framework controls; no test model; no due dates/recurrence/evidence expiry |
| 2 | Integrations + continuous monitoring | ~8% | One real integration (Google users); no automated tests; no cloud/asset discovery |
| 3 | Policies, Trust Center, reports, AI | ~45% | No template library; Trust Center v1; no acknowledgement campaigns |
| 4 | Risk, vendors, incidents | ~35% | Vendors can't answer assessments (no portal); fixed risk scoring. Incidents already ahead of Scrut |
| 5 | Audits + people | ~33% | No external auditor portal; access reviews shallow; no onboarding/offboarding |
| 6 | Platform foundations | ~37% | No MFA/SSO/invites/password reset; hard-coded roles; no API/tasks inbox |
| | **Overall (simple mean)** | **~31%** | |

## Cross-cutting dependencies (build these first, they unblock everything)
1. **Security hardening** (open redirect on login `next`, GET logout, any-user-can-create-org, per-process login throttle,
   plaintext Google OAuth tokens, `db.create_all()` at boot, CDN assets without SRI).
2. **Encrypted secret storage** (Fernet; `cryptography` dependency) — needed by every connector and by Google tokens.
3. **Scheduler/job runner** (the `flask run-daily-jobs` CLI exists; needs a cron/systemd timer installed by the owner).
4. **Owner-as-user + due dates + recurrence + evidence expiry + unified Tasks/My-work inbox** — feeds notifications,
   audits, vendors, risks, policies.
5. **Test engine** (TestDefinition / OrgTest / TestRun) — the heart of "continuous compliance"; internal tests first.

## Waves (each wave = parallel streams with disjoint files; ONE stream owns migrations per wave)

**Wave 1 — Foundations & quick wins** (target: 31% -> ~40%)
- A. Platform hardening + invites + password reset + MFA(TOTP) + member management (sec 6 P1-P3)
- B. Compliance workflow: due dates/recurrence/evidence expiry, control owner as user, comments, control history,
  unified Tasks inbox, persisted notification prefs + email digest (sec 1 items 1-2, sec 6 P6-P7)
- C. Risk/vendor quick wins: fix `/api/risks/matrix` 5-level bug, status/treatment enums, risk owner+review date,
  vendor recurrence + archive instead of delete, configurable scoring matrix (sec 4 quick wins, item 5)
- D. Policy acknowledgement campaigns + reminders; questionnaire answer library (sec 3 items 1, 4)
- E. Connector foundation: encrypted credentials, Connection/Resource/Test/Run tables, base class, sync hook in run-daily-jobs,
  upgraded /tests UI, internal test library (30-40 tests from MIGRC's own data) (sec 2 foundation + sec 1 item 4)

**Wave 2 — The differentiators** (target: ~40% -> ~55%)
- External auditor portal (invites, per-audit scope, requests, comments, expiry, audit trail) (sec 5)
- External vendor portal (tokenized links, expiry, scoring, review, PDF) (sec 4)
- Unified control library + requirement mapping (sec 1)
- Connectors: Google Workspace extension, GitHub (sec 2)
- Policy template library (80+ original, AI-drafted + human-reviewed) (sec 3)
- OIDC SSO (Google/Okta/Entra) (sec 6)

**Wave 3 — Scale-out** (target: ~55% -> ~70%)
- AWS connector (+ CloudFormation read-only role), Okta, Slack, Jira, Fleet/MDM
- Trust Center v2 (per-tenant slugs, access requests, subprocessors, FAQ, custom domain)
- Access reviews with sign-off, onboarding/offboarding engine, training v2 (quizzes/certificates)
- Report registry (CSV/XLSX/scheduled), AI assistants (Q&A, risk/remediation suggestions)
- REST API + keys + webhooks, custom roles + scoping, global search/tags

**Later / needs owner decisions or paid access**: Azure/GCP, endpoint agent, SCORM/phishing, MSP console, Stripe billing,
Scrut's vetted 80+ connector marketplace and proprietary test catalog (cannot be replicated; rebuild from public benchmarks).

## What needs the owner
- Credentials/sandbox accounts per connector (AWS role, GitHub App/PAT, Okta, Slack, Jira).
- `crontab -e` / systemd timer for `run-daily-jobs`; `opencode auth login` for the OpenCode path.
- Decisions: framework-visibility repair for existing orgs; billing/plans; custom domain for Trust Center.
- Rotate DB password + Cline key (exposed in session output).

## Honest ceiling
~65-75% practical parity is achievable without Scrut's partner ecosystem; the remaining gap is vendor-curated
connector breadth, proprietary test/mapping catalogs, and auditor-network marketing, not engineering depth.
