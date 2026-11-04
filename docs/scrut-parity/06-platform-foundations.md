# Section 6: Platform Foundations - Scrut parity analysis and plan

Date: 2026-11-04. Method: public sources only (Scrut help center and marketing pages, review and comparison sites). No Scrut application or API hosts were contacted. Where a fact is unconfirmed it is labelled UNCONFIRMED.

## 1. Scrut platform spec (public sources)

| Area | What public sources say | Source |
|---|---|---|
| Roles | Three platform roles. Admin: all modules, departments, frameworks, user CRUD, settings. Contributor: limited to granted modules and assigned departments; completes assigned tasks; cannot touch artifacts without a department assignment. Auditor: view-only on assigned modules, can be limited to specific frameworks (e.g. ISO 27001), managed via Audit Center. "Employees" are not a role: People-module records who only see the training/policy-acceptance portal. | https://help.scrut.io/docs/user-roles |
| Departments as RBAC scope | Contributors are scoped by department; department owners are set in the setup wizard and editable in Settings > Manage Departments. | https://help.scrut.io/docs/setup-wizard |
| SSO | Login SSO via Okta using an OIDC app (Client ID/Secret entered in the Identity Providers library; enabled in Settings; region-specific base URL US/EU/India). Google Workspace SSO via OAuth connection, enabled in Settings > Administration. Microsoft Entra is listed as a supported IdP. SAML 2.0 is claimed by third-party directories only: UNCONFIRMED. | https://help.scrut.io/docs/integrating-okta ; https://help.scrut.io/docs/integrating-google-workspace ; https://www.stitchflow.com/user-management/scrut/manual |
| SCIM | Okta's catalogue lists SCIM; other sources say it is undocumented or gated to enterprise plans. UNCONFIRMED. | https://www.okta.com/integrations/scrut-automation/ ; https://www.stitchflow.com/scim/scrut |
| MFA | Scrut states it requires MFA for every account in its own security program; no public customer-facing MFA-enforcement page found (login MFA likely delegated to IdP). | https://www.scrut.io/company/security |
| Multi-entity | "Multi-Entity Compliance" appears on the enterprise solutions page; implemented via workspaces per third-party summary; reviewers say complex multi-subsidiary setups feel restrictive. No public MSP/consultant partner console found (G2 lists implementation service providers only). | https://www.scrut.io/solutions/enterprise-software ; https://www.rfp.wiki/legal-compliance/scrut-automation |
| API / webhooks | FAQ stresses "API-driven architecture" and 80+ integrations; no public developer docs, API-key page or webhook docs found. Treat as: integrations-in, limited public outbound API. | https://www.scrut.io/faqs/general |
| Notifications | Settings > Notifications: personal task reminders (overdue, due soon, pending approval) delivered Monday or daily; Slack alerts (mentions, Trust Vault requests); training email reminders; evidence review-cycle reminders; "Scrut Digest" summarising compliance progress per framework with due dates and pending items. Jira ticket sync with assignee and due date. | https://help.scrut.io/docs/configuring-slack-reminders ; https://help.scrut.io/docs/my-tasks-task-center ; https://help.scrut.io/docs/setting-an-evidence-review-cycle |
| Slack | Integration pulls users into People, checks MFA/offboarding, and a Scrut Teammates bot answers compliance questions in Slack. | https://help.scrut.io/docs/integrating-slack |
| Tasks center | "My Tasks" tab in Task Center: personal queue with pending/completed counters; corrective actions with assignee, approver (should differ), due date; evidence tasks with recurrence and review date. | https://help.scrut.io/docs/my-tasks-task-center ; https://help.scrut.io/docs/corrective-action-workflow |
| Onboarding | Setup Wizard, 4 sections / 11 steps: org details; IdP; department owners; cloud providers; internal audit dates; policy variables; MDM; background verification; training; required policies; tech stack. "I Don't Need This" skip; auto-save; Invite Contributor; Teammates chat help. | https://help.scrut.io/docs/setup-wizard |
| Activity / audit log, export, custom fields/tags, global search, localisation | Not found in public docs searched: UNCONFIRMED. Reports export exists (types-of-reports page). | https://help.scrut.io/docs/types-of-reports |
| Dashboards | Single multi-framework dashboard; auditor view through Audit Center; employee portal. No evidence of per-role dashboards beyond that. | https://www.scrut.io/faqs/general |
| Pricing | Not published. Third-party estimates about USD 15k/yr entry (20 employees) up to 10-30k enterprise; Scrut says all plans include all core modules and frameworks (audit fees extra). SCIM possibly gated. | https://www.trustradius.com/products/scrut-automation/pricing ; https://www.scrut.io/faqs/general |
| Platform's own security | ISO 27001, ISO 42001, SOC 2, ISO 27701 claimed; TLS in transit, encryption at rest, least-privilege RBAC, MFA for every account; public trust center. Does not train shared models on customer data. | https://www.scrut.io/company/security ; https://trust.scrut.io/ |

Caveat: third-party sources (Stitchflow, soc2auditors.org, comparison blogs) conflict and may be competitor-authored.

## 2. MIGRC current state (code reading)

- Identity: `User` (email+password, werkzeug hash), global `User.role` fallback, per-org `OrganizationMembership.role`. `ROLE_PERMISSIONS` is a hard-coded dict of 4 roles and 5 permissions (`write, delete, manage_users, audit_write, review_evidence`) in `app/models.py`. Enforcement via `@require_permission` in `app/utils.py`. Only `/register` (admin creates user with a set password, or adds existing user); no invite email, no password reset, no role change/remove-member UI route found, no password policy.
- Login: in-memory per-process throttle (10 attempts / 15 min) in `app/routes/auth.py`; no MFA; Google OAuth exists only for Workspace directory sync (`google_oauth.py`), not login. Logout is GET.
- Multi-tenancy: shared DB, `organization_id` columns, `g.current_org` via session (`services/org_context.py`), switch and create-org routes, `test_tenant_isolation.py`. Any user can create an org (becomes Admin). No tenant-scoped query guard (convention only).
- Notifications: in-app `Notification` with dedupe_key, bell dropdown, daily generation (`ensure_notifications_for_today`, `flask run-daily-jobs`), optional SMTP email per notification (one email per event, no digest). Settings > Notifications toggles are decorative (not persisted).
- Activity log: `ActivityLog` (org, user, action, entity, 300-char description), filter UI, CSV export. No IP, no before/after, no immutability, no auth events.
- Onboarding: `/setup` wizard with `SetupTask` + data-derived completion, org profile, department owners, audit scheduling.
- Settings: 3 tabs (Organization, Notifications, Users & Roles).
- Owners: mostly free-text `owner` String columns (Risk, Policy, Control status, Asset, Access review); only Incident.owner_id, finding remediation assignee, policy assignees are FKs.
- API: only `/api/dashboard/stats` (session auth). No keys, webhooks, OpenAPI.
- Search: sidebar box filters nav items only (client JS).
- Hardening seen: CSRF (Flask-WTF), HttpOnly/Lax/Secure cookies, SECRET_KEY warning, CSV cell sanitising. Not seen: security headers/CSP, session timeout, rate limiting beyond login, encryption of Google tokens (stored plaintext Text columns), `db.create_all()` at startup alongside Alembic, CDN assets without SRI.

## 3. Parity table

| Capability | Scrut | MIGRC | Status |
|---|---|---|---|
| Fixed roles (Admin/Contributor/Auditor/Viewer) | Yes | 4 roles incl. Auditor | Has |
| Department/module-scoped Contributor | Yes | No scoping; roles are org-wide | Missing |
| Framework-scoped auditor | Yes | No | Missing |
| Custom/granular roles | Limited (3 fixed; FAQ claims "fine-grained") | No | Partial/Missing |
| Invite users by email | Yes | Admin sets password; no email invite | Partial |
| Password reset / policy | Standard | None | Missing |
| SSO (OIDC Okta/Google) | Yes | None for login | Missing |
| SAML / SCIM | Unconfirmed | None | Missing (parity unclear) |
| MFA | Yes (internal), IdP for customers | None | Missing |
| Multi-org switching | Yes (entities/workspaces) | Yes | Has |
| Cross-org rollup / MSP console | No public evidence | Switcher only | Partial (beyond Scrut) |
| REST API + keys | Not public | Single session endpoint | Missing |
| Webhooks | Not public | None | Missing |
| In-app notifications | Yes | Yes | Has |
| Email notifications | Yes + digest | Per-event, off by default | Partial |
| Slack/Teams alerts | Slack | None | Missing |
| Per-user notification prefs | Yes | UI-only, not stored | Partial |
| Scheduled digest | Yes | None | Missing |
| Activity/audit log | Presumed | Yes, basic + CSV | Partial |
| Tasks / My Tasks | Yes | None unified | Missing |
| Per-record owners (FK user) | Yes | Mostly free text | Partial |
| Setup wizard | Yes (11 steps) | Yes (data-derived) | Has (fewer steps: no IdP/cloud/MDM/BGV step coupling) |
| Data export | Reports | CSV + PDF | Has |
| Custom fields / tags | Unconfirmed | None | Missing |
| Global search | Unconfirmed | Nav filter only | Missing |
| Role dashboards | Limited | One dashboard | Partial |
| Localisation | Unconfirmed | English only; timezone field in profile | Missing |
| Billing / plan gating | Quote-based | None (self-hosted) | N/A (optional) |
| Platform security posture | ISO27001/SOC2, MFA, encryption | Partial hardening | Partial |
| Packaging (Docker, env config) | SaaS | gunicorn/start.bat only, no Dockerfile | Partial |

Scoring (Has=1, Partial=0.5, Missing=0), 26 scored rows (excluding Billing N/A, SAML/SCIM counted once, MSP row excluded as Scrut has no public equivalent): Has 5, Partial 10, Missing 11 gives (5 + 5)/26 = about 38%. Against capabilities Scrut publicly documents (roles, SSO, tasks, notifications, wizard, Slack), honest parity is roughly **35-40%**. Multi-tenant core and wizard are strong; identity, tasks, integrations-out, and notifications depth are the gaps.

## 4. Plan (ordered by value)

Effort: S under 2 days, M 3-7 days, L over 1 week.

### P1. Security baseline hardening (S-M) - do first, tenant data
See checklist section 5. Add `app/security.py` (headers, session lifetime), move login throttle to DB/Redis, encrypt OAuth tokens.

### P2. Invites, password reset, member management (M)
- WHAT: email invite with signed token, forgot-password, change role / deactivate / remove member, password policy (min 12, zxcvbn-lite, HIBP optional).
- HOW: `itsdangerous.URLSafeTimedSerializer` tokens (24h, single-use via `Invitation` table). Tables: `invitations(id, org_id, email, role_id, token_hash, invited_by, expires_at, accepted_at)`. Remove plain password creation in `/register`.
- WHERE: `app/routes/auth.py` (`/invite/<token>`, `/forgot`, `/reset/<token>`), new `app/routes/members.py` (`POST /settings/members/<id>/role|remove`), `app/services/mail.py` templates, `templates/settings.html` Users tab, `templates/accept_invite.html`. Always log to ActivityLog.

### P3. MFA (TOTP + recovery codes) (M)
- WHAT: optional per user, enforceable per org ("require MFA for all members").
- HOW: `pyotp` + `qrcode`. Columns on User: `totp_secret_enc` (Fernet with key from env `MIGRC_FIELD_KEY`), `mfa_enabled`, `mfa_enrolled_at`; table `mfa_recovery_codes(id,user_id,code_hash,used_at)` (10 codes, hashed). Login flow: password ok -> `session['pre_mfa_user_id']` (not logged in) -> `/login/mfa` verify with 30s window +/-1, replay guard (`last_totp_step`), throttle. Org column `Organization.require_mfa`; before_request redirects un-enrolled members to enroll page.
- WHERE: `auth.py` (split `login_user` call), new `app/routes/security.py` (`/settings/security`, enroll, disable, regenerate codes), `templates/mfa_*.html`, `models.py`, migration. Tests in `test_routes.py`.

### P4. OIDC SSO (Google, Microsoft Entra, Okta, generic) (M); SAML later (L)
- WHAT: per-org identity providers; login via "Sign in with SSO" using email domain discovery; JIT provisioning with default role; optional "enforce SSO" (disables password for that domain, break-glass admin retained).
- HOW: `Authlib` (OIDC discovery, PKCE, state/nonce, verify ID token `iss/aud/exp`, require `email_verified`). Tables: `identity_providers(id, org_id, kind, issuer, client_id, client_secret_enc, allowed_domains JSON, default_role_id, enforce, enabled)`, `user_identities(id,user_id,idp_id,subject UNIQUE(idp_id,subject))`. Match on (idp, sub) first, then verified email; never auto-link across orgs without membership. SAML via `python3-saml` or `pysaml2` (SP metadata endpoint, ACS, signed assertions required, clock skew 60s, replay cache) as phase 2. SCIM v2 (`/scim/v2/Users`, `/Groups`, bearer token per org) phase 3, maps groups to roles.
- WHERE: new `app/routes/sso.py`, `app/services/oidc.py`, reuse pattern from `google_oauth.py`, UI under Settings > Security, `templates/login.html` (SSO button/email-first).

### P5. Granular custom roles and department scoping (M-L)
- WHAT: org-defined roles built from permission atoms, plus optional scope (departments, frameworks) to mirror Scrut Contributor/Auditor.
- HOW: tables `roles(id, org_id NULL for built-ins, name, is_system)`, `role_permissions(role_id, perm)`, `membership_scopes(membership_id, scope_type['department'|'framework'], scope_value)`. Expand perm atoms: `<module>.view|write|delete` for risks, policies, vendors, assets, people, compliance, audits, incidents, plus `evidence.review`, `users.manage`, `settings.manage`, `api.manage`, `audit_log.view`. Migrate `ROLE_PERMISSIONS` into seed rows; `OrganizationMembership.role_id` FK (keep `role` string as legacy until migrated). `User.has_permission` reads cached set on `g`. Add `@require_permission('risks.write')` per route; query helpers `scoped(query, Model)` applying department/framework scopes. Auditor framework scope enforced in compliance/audits queries.
- WHERE: `models.py`, `utils.py`, every blueprint decorator (mechanical), `templates/settings.html` Roles tab, `app/seed.py`. Add a permission-matrix test that hits every route per role.

### P6. Unified Tasks / My Work inbox plus real owners (M-L)
- WHAT: one queue per user of everything they own or must act on, mirroring Scrut My Tasks: overdue, due soon, pending approval; plus standalone tasks with assignee, approver, due date, recurrence.
- HOW: convert free-text `owner` columns to `owner_id` FK (Risk, Policy, ControlStatus, Asset, AccessReview, Vendor, Audit finding), migrating by name/email match with fallback to keep old text. New `tasks(id, org_id, title, description, assignee_id, approver_id, due_date, status, priority, recurrence_rule, entity_type, entity_id, created_by, completed_at)`. "My work" is a service aggregating: tasks, policies awaiting review/acceptance, evidence rejected, findings/remediations assigned, risk treatments/milestones due, access reviews, vendor reassessments, training enrollments. Dedupe against `Notification` so each item notifies once.
- WHERE: `app/models.py` (Task), `app/services/my_work.py`, `app/routes/tasks.py`, `templates/tasks.html`, nav entry and dashboard widget, daily job generates recurrences.

### P7. Notification preferences, email digest, Slack/Teams (M)
- WHAT: persisted per-user per-type preferences (in-app/email/off), daily/weekly digest, Slack and Teams incoming-webhook channels per org.
- HOW: `notification_prefs(user_id, org_id, type, channel_email, channel_inapp, digest ENUM none|daily|weekly)`; `org_webhooks_chat(org_id, kind slack|teams, url_enc, event_types JSON)`. `send_digest` in `flask run-daily-jobs` renders one email (HTML + text) per user summarising My Work plus compliance score deltas. Slack: POST Block Kit JSON to webhook; Teams: Adaptive Card. Wrap in retry with timeout 5s; store `last_error`. Replace decorative toggles in `settings.html`. Respect SSRF protection (see checklist). Use background worker (RQ/APScheduler) rather than sending inside request.
- WHERE: `app/services/notifications.py` (`_maybe_email` consults prefs), new `app/services/digest.py`, `app/services/chat_webhooks.py`, `app/cli.py`, settings tab.

### P8. REST API with API keys and outbound webhooks (L)
- WHAT: `/api/v1` read (and gated write) for controls, risks, policies, vendors, assets, employees, incidents, evidence; org-scoped keys; signed outbound webhooks for events (control status change, risk created, evidence rejected, incident opened, policy published).
- HOW: `api_keys(id, org_id, name, prefix, key_hash (sha256), role_id/scopes JSON, created_by, last_used_at, expires_at, revoked_at)`; show full key once; `Authorization: Bearer migrc_<prefix>_<secret>`; constant-time compare; per-key rate limit (Flask-Limiter + Redis). `webhook_endpoints(id, org_id, url, secret_enc, events JSON, enabled)` and `webhook_deliveries(id, endpoint_id, event, payload, status, attempts, next_attempt_at, response_code)`. Sign `X-MIGRC-Signature: t=<ts>,v1=HMAC_SHA256(secret, ts.payload)`; retries with exponential backoff; 5xx/timeout handling; replay window documentation. Pagination (`limit/cursor`), `flask-smorest` or `apiflask` for OpenAPI spec at `/api/v1/openapi.json`. CSRF-exempt only for the API blueprint using token auth.
- WHERE: new `app/api/` package (`__init__.py`, `auth.py`, resources), `app/services/webhooks.py` emit hook called from `log_activity` (single choke point), settings tab "API & Webhooks".

### P9. Global search and tags/custom fields (M each)
- Search: Postgres `tsvector`/`pg_trgm` (SQLite fallback LIKE) over controls, policies, risks, vendors, assets, employees, incidents, evidence, always filtered by `organization_id` and role permissions. `GET /search?q=` plus typeahead JSON endpoint; replace `#sidebarSearch` nav filter with Cmd-K palette. Files: `app/services/search.py`, `app/routes/search.py`, `base.html`, `static/js`.
- Tags: `tags(id, org_id, name, color)`, `taggings(tag_id, entity_type, entity_id)`; custom fields: `custom_field_defs(id, org_id, entity_type, key, label, type[text|number|date|select|user], options JSON, required)` and `custom_field_values(def_id, entity_id, value JSON)`. Surface in list filters and CSV export. Files: `models.py`, `app/services/tags.py`, partial `_tags.html`.

### P10. Audit log upgrade (S-M)
Add `ip`, `user_agent`, `request_id`, `before/after` JSON, `outcome`; log auth events (login, failure, MFA, role changes, API key use, export); widen description; make append-only (DB trigger/permissions, optional hash chain `prev_hash`); retention setting; JSON export and syslog/webhook streaming. Files: `models.py`, `services/activity.py`, `routes/main.py`.

### P11. MSP / consultant console (L) - exceeds Scrut public parity
- WHAT: partner account that manages many client orgs with rollup view.
- HOW: `Organization.parent_org_id` or `partners` table; `PartnerMembership(user_id, partner_id, role)`; grants implicit access to child orgs with partner role mapping, audit-logged "acting in client org" banner; cross-org rollup page (score per framework, overdue tasks, expiring evidence); org templates (clone frameworks/policies/setup). Restrict creation of orgs (`ALLOW_ORG_CREATE` config; currently any user can create) .
- WHERE: `routes/organizations.py`, `services/org_context.py`, new `routes/partner.py`, `templates/partner_dashboard.html`.

### P12. Setup wizard parity (S-M)
Add steps: connect IdP/SSO, invite contributors (email), cloud/MDM/BGV integration stubs linked to Integrations page, policy variables, "I don't need this" skip with later resume, progress persistence. Files: `routes/setup.py`, `setup_wizard.html`.

### P13. Role dashboards and localisation (M)
Dashboard variants keyed by role (Admin: posture; Contributor: My work; Auditor: audit progress; Viewer: read-only summary). i18n via Flask-Babel, extract strings, per-user locale and timezone, replace `datetime.utcnow` display with tz-aware rendering. Defer until after P1-P8.

### P14. Billing/plan gating (optional, M)
Stripe Checkout + webhooks: `subscriptions(org_id, stripe_customer_id, plan, seats, status, current_period_end)`, `feature_flags` per plan, decorator `@requires_plan('sso')`. Only for hosted offering; keep disabled by default (`BILLING_ENABLED=false`). Scrut itself is quote-based, so low priority.

### P15. Packaging (S)
Dockerfile (non-root, gunicorn), docker-compose with Postgres + Redis + worker, `.env.example`, healthcheck endpoint `/healthz`, remove `db.create_all()` at boot in favour of `flask db upgrade`, pinned requirements with hash check, backup/restore doc, version endpoint.

### Suggested sequence
P1 -> P2 -> P3 -> P6 (owners FK first) -> P7 -> P4 (OIDC) -> P10 -> P5 -> P8 -> P9 -> P12 -> P11 -> P13 -> P15 (can run alongside) -> P14 optional.

## 5. Security-hardening checklist for the platform itself

Authentication and session
- [ ] Enforce strong secrets: refuse to boot in non-debug if `SECRET_KEY` is default (currently only warns).
- [ ] Password policy plus Argon2id/scrypt (werkzeug scrypt ok; set work factor), reset tokens single-use, short-lived, hashed at rest.
- [ ] MFA (P3), SSO (P4), org "enforce MFA/SSO" settings; break-glass local admin.
- [ ] Login throttling and lockout stored in Redis/DB (current dict is per-process and resets on restart); throttle per account and per IP; throttle MFA and reset endpoints; generic error messages (avoid user enumeration on invite/reset).
- [ ] Session: `PERMANENT_SESSION_LIFETIME` (e.g. 8h), idle timeout, rotate session on login (`session.clear()` before login_user), server-side revocation (session version column bumped on password/role change), "log out other sessions".
- [ ] Make `/logout` POST with CSRF; validate `next` parameter in login (currently redirected unvalidated: open redirect; restrict to relative same-host paths).
- [ ] Cookie flags: Secure, HttpOnly, SameSite Lax, `__Host-` prefix when possible.

Tenant isolation
- [ ] Central tenant guard: base query class or SQLAlchemy `with_loader_criteria` event adding `organization_id = g.current_org.id` to all tenant models; fail closed if no org.
- [ ] Authorise object IDs on every `<int:id>` route (IDOR tests per blueprint; extend `test_tenant_isolation.py` to iterate all routes automatically).
- [ ] File uploads: store per-org paths, random names, serve through authenticated route, check MIME and extension, antivirus hook, `MAX_CONTENT_LENGTH` already 10MB; no SVG inline serving (logo SVG allowed in IMAGE_EXTENSIONS: sanitise or serve with `Content-Security-Policy: sandbox`).
- [ ] Postgres Row-Level Security as defence in depth (set `app.current_org` per connection).
- [ ] Restrict `create_organization` (any logged-in user can mint orgs): add config switch.

Data protection
- [ ] Encrypt secrets at rest (Google tokens, IdP secrets, webhook secrets, TOTP seeds) with Fernet/KMS; rotate keys.
- [ ] TLS everywhere, HSTS, DB over TLS, encrypted volumes and backups, tested restore, per-tenant export and delete (offboarding/GDPR).
- [ ] Never log secrets/tokens; scrub PII from app logs (note repo contains `*.log` files; keep them out of git and rotate).
- [ ] AI features: do not send tenant data to external providers without per-org opt-in; document data flows (anthropic and OpenCode dispatch); redact secrets before prompts.

HTTP hardening
- [ ] Security headers (Flask-Talisman): CSP (self-host Font Awesome and fonts, drop CDN or add SRI, avoid inline `onclick` such as in settings.html), `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `frame-ancestors 'none'` (except Trust Center badge if embedding intended).
- [ ] Rate limiting (Flask-Limiter + Redis) for all POST and API routes; request size limits.
- [ ] CSRF on all state-changing routes; remove GET state changes; API blueprint token-only.
- [ ] Output encoding: audit `|safe` usage and markdown/policy rendering for stored XSS; CSV formula injection already handled (`sanitize_cell`), keep.
- [ ] SSRF guard for webhooks/Slack/Teams/OIDC discovery: allow https only, resolve and block private/link-local/metadata IP ranges, no redirects, timeouts.
- [ ] Public Trust Center and NDA endpoints: rate limit, captcha, avoid enumeration, store consent audit (already stores IP).

Authorisation and audit
- [ ] Permission-matrix test per role per route; deny by default for new routes (before_request check that every endpoint is decorated or explicitly public).
- [ ] Immutable, expanded audit log (P10); alerts on privilege changes; export to SIEM.
- [ ] API keys hashed, scoped, expiring, last-used visible, revocable.

Operations and supply chain
- [ ] Run non-root, read-only filesystem where possible, separate DB user with least privilege; no `db.create_all()` in prod.
- [ ] Dependency scanning (pip-audit, Dependabot), pinned hashes, SBOM, secret scanning in CI, bandit/semgrep; `.env` and DB files excluded from git.
- [ ] Backups encrypted, retention documented, DR runbook; `/healthz` without sensitive info; disable debug and Werkzeug console in prod.
- [ ] Vulnerability disclosure policy (`security.txt`), incident response runbook, dogfood: track MIGRC's own SOC 2/ISO 27001 controls inside MIGRC.

## 6. Source list
- https://help.scrut.io/docs/user-roles
- https://help.scrut.io/docs/setup-wizard
- https://help.scrut.io/docs/integrating-okta
- https://help.scrut.io/docs/integrating-google-workspace
- https://help.scrut.io/docs/integrating-slack
- https://help.scrut.io/docs/configuring-slack-reminders
- https://help.scrut.io/docs/my-tasks-task-center
- https://help.scrut.io/docs/corrective-action-workflow
- https://help.scrut.io/docs/setting-an-evidence-review-cycle
- https://help.scrut.io/docs/types-of-reports
- https://www.scrut.io/faqs/general
- https://www.scrut.io/company/security
- https://trust.scrut.io/
- https://www.scrut.io/solutions/enterprise-software
- https://www.okta.com/integrations/scrut-automation/
- https://www.stitchflow.com/scim/scrut ; https://www.stitchflow.com/user-management/scrut/manual
- https://www.trustradius.com/products/scrut-automation/pricing
- https://www.rfp.wiki/legal-compliance/scrut-automation
- https://soc2auditors.org/software/scrut/
