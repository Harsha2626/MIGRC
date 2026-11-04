# Scrut parity - Section 2: Integrations, Continuous Monitoring and Assets

Sources: public Scrut help center and marketing pages only (no Scrut app/API hosts were contacted). Where public pages do not say something, it is marked UNKNOWN rather than guessed.

## 1. Scrut's integration and automation spec (public sources)

### 1.1 Catalog (help.scrut.io/docs/integrations-overview; scrut.io/integrations)
Scrut claims 80+ integrations (scrut.io/faq); the help-center catalog lists roughly 180 named tiles in 19 categories:

| Category | Named integrations |
|---|---|
| Cloud | AWS, GCP, Azure, DigitalOcean, Heroku, Vercel |
| Identity | Google Workspace, Okta (IDP and SSO as separate tiles), Entra ID, Auth0, JumpCloud, OneLogin, PingOne |
| HRIS | BambooHR, Rippling, Workday, ADP, Gusto-class peers (Deel, Personio, Hibob, Darwinbox, Keka, Zenefits, UKG, SAP SuccessFactors, Paylocity, Paycom, Zoho and ~15 more) |
| Version control | GitHub, GitLab, Bitbucket, Azure DevOps |
| Project mgmt / ticketing | Jira, Linear, Asana, ClickUp, Trello, ServiceNow, Azure DevOps, Monday, Shortcut, Freshservice, ServiceDesk Plus, Zendesk |
| Comms | Slack (plus Dialpad, SendGrid, Fireflies) |
| MDM / endpoint | Jamf Pro, Kandji, Intune, Hexnode, Fleet, Kolide, NinjaOne, Sophos, Endpoint Central, JumpCloud, Island, Kitecyber |
| XDR / threat | CrowdStrike, SentinelOne |
| Vulnerability / code scanning | Snyk, Tenable, Qualys, SonarCloud, Sentry, Aikido, Microsoft Defender Endpoint |
| Background check | Checkr, Certn, SpringVerify, ZincWork |
| Security training | KnowBe4, EC Council, Phished, ThreatCop |
| Monitoring / data | Datadog, New Relic, Sumo Logic, Snowflake, Databricks, MongoDB, BigQuery, Tableau |
| Policy mgmt | Confluence, SharePoint, PandaDoc |
| Web security | Cloudflare |
| Misc / CRM / long tail | Salesforce, HubSpot, Stripe, Notion, OpenAI, Anthropic, Dropbox etc. |

Plus the Scrut Agent (osquery-based endpoint agent) and AWS Marketplace listing.

### 1.2 How connection works
- AWS (help.scrut.io/integrating-aws): CloudFormation template (stack "ScrutIntegrationRole") creates a cross-account IAM role with AWS-managed SecurityAudit + ReadOnlyAccess. The customer pastes the role ARN plus an account nickname. Then picks services, regions and optional tag filters; a discovery job runs. Metadata/config only, no data-plane reads (no S3 objects, no secret values). Multi-account supported. Services: IAM, EC2, VPC, S3, Backup, EKS, RDS, Inspector, Security Hub, CodeCommit, CloudWatch, ELB, SSM, DocumentDB, DLM.
- Cadence: AWS syncs every 24 h (first sync up to 24 h). A "Test Now" button re-scans a single test on demand. Docs also say tests "run continuously" and some show a "Continuous Monitoring" badge instead of next-scan time (real-time ones). Scrut Agent syncs every 3 h.
- Other integrations: public pages do not describe auth steps per tool (UNKNOWN; presumably OAuth or API token per tile).
- Data flow by category: HRIS pushes name, email, hire/exit date, department, manager to People -> Employees. MDM pushes OS name/version, antivirus, screen lock, disk encryption. IdP gives SSO and sometimes the employee list. Background checks land in the employee task list. Policy tools import/sync policies. Project tools create issues from Scrut. Version control feeds an evidence task "Code Review Results" (PR data). Inspector/Security Hub findings feed a Vulnerabilities module (track, assign, remediate).
- Scrut Agent (help.scrut.io/docs/scrut-agent-*): osquery-based, "not a replacement for MDM"; checks disk encryption, screen lock, antivirus; Windows 10/11, macOS 13-26, Ubuntu/Fedora/Pop!_OS/Garuda. Installed by employees from an Employee Training Portal. A Capterra reviewer reports slow agent sync.

### 1.3 Tests and evidence mapping (help.scrut.io/docs/getting-started-with-tests-in-scrut, cloud-test-details-page)
- Test types: Automated (cloud AWS/Azure/GCP and other integrations; includes vuln scans, code reviews), "Scrut-recommended" tests based on best practice and CIS benchmarks (exact CIS test count is NOT published), plus policies and evidence tasks in the same Tests module.
- Statuses: Passing, Fix Required, Ignored. Ignored tests do not count toward compliance % and are not resurfaced.
- Hierarchy: Framework -> Requirement -> Control -> implementation items (policies, evidence tasks, automated tests). A control is compliant only when all linked items are Passing and no open audit findings exist; this rolls up to requirements and framework %. A Mapping filter finds tests not linked to any control. Connecting/disconnecting integrations adds/removes tests.
- Cloud test detail page: title, status, mapped frameworks, AI-generated step-by-step remediation, "Flagged Resources" table (per-resource assign/ignore, side drawer with config metadata, CSV export), assignees at test or resource level, Controls and Requirements list, Test Now.
- Alerting: no public detail on Slack/email alerting for failing tests (UNKNOWN); Slack integration is listed.
- Reviews: G2/Capterra praise automated evidence collection; complaints are long-tail integration gaps (e.g. GoDaddy), limited custom-integration/API flexibility, slow agent sync, quote-only pricing. No sourced head-to-head Vanta/Drata integration count found.

Source URLs: https://help.scrut.io/docs/integrations-overview , https://www.scrut.io/integrations/ , https://help.scrut.io/integrating-aws , https://help.scrut.io/docs/getting-started-with-tests-in-scrut , https://help.scrut.io/docs/cloud-test-details-page , https://help.scrut.io/docs/automated-tests-tab , https://help.scrut.io/docs/scrut-agent-supported-operating-systems , https://help.scrut.io/docs/scrut-agent-faqs-troubleshooting , https://scrut.io/post/automated-controls-testing , https://scrut.io/faq , https://www.capterra.com/p/10012083/Scrut/reviews , https://www.rfp.wiki/legal-compliance/scrut-automation

## 2. MIGRC current state and parity table

Current code facts (read-only review):
- `app/routes/integrations.py`: static PLANNED_INTEGRATIONS list (AWS, GCP, Azure, Okta, Entra, Slack, Jira) - none implemented.
- Only real integration: Google Workspace (`google_oauth.py`): OAuth with scope admin.directory.user.readonly, manual "sync" button, upserts Employee (name, status). Tokens stored PLAINTEXT in `google_workspace_connections` (access_token, refresh_token); single connection per org (unique); not run by `run-daily-jobs`; no error/health state.
- `Asset`: flat manual table (type, resource_id, region, cloud_provider, owner, classification), CRUD + CSV export; 12 type buckets already mirroring Scrut's asset categories. No source/external-id/last-seen, no discovery.
- `Employee.monitoring_agent_installed` / `device_security_compliant` are manually-set booleans. `EmployeeAccess` links employee to Vendor only.
- `app/cli.py run-daily-jobs`: per-org loop, failure-isolated, snapshots + notifications only; good scheduling hook. No sync/test framework, no secrets/crypto library (cryptography not in requirements; SECRET_KEY only).
- Evidence has `source_type`, file-based; ControlStatus is manual per-org.

| Capability | Scrut | MIGRC | Rating |
|---|---|---|---|
| Integration catalog breadth (80+) | yes | 1 real (+7 placeholders) | Missing (~1%) |
| Identity/employee sync (Google) | yes | manual button, users only | Partial |
| Okta/Entra/other IdP | yes | none | Missing |
| HRIS sync | 25+ | none | Missing |
| Cloud connect (AWS/GCP/Azure) read-only | yes | none | Missing |
| Cloud asset auto-discovery | yes | manual assets only | Missing (UI shell Has) |
| Asset inventory UI/export/categories | yes | yes | Has |
| Automated test engine + CIS-based tests | yes | none | Missing |
| Test -> control -> compliance % rollup | yes | none (manual ControlStatus) | Missing |
| Auto-collected evidence | yes | none | Missing |
| Pass/fail history, Test Now, ignore, assign, remediation guidance | yes | none (AI evidence review exists, different) | Missing |
| Version control / PR evidence | yes | none | Missing |
| Ticketing (Jira etc.) | yes | none | Missing |
| Slack alerts | yes | none (email notifications exist) | Partial-ish (channel only) |
| MDM sync | 12 | none | Missing |
| Endpoint agent | yes | boolean fields only | Missing |
| Vulnerability scanner ingestion | yes | none | Missing |
| Credential encryption at rest | n/a public | plaintext tokens | Gap |
| Scheduled sync infra | yes | run-daily-jobs exists | Partial |

Honest parity for this section: about 8% (asset UI, one OAuth identity sync, cron scaffolding). Weighted by value (tests/evidence automation is the core of Scrut's differentiation) it is effectively 5%.

## 3. PLAN

### 3.1 Architecture

Package `app/connectors/`:
- `base.py`: `class Connector` (abstract) with class attrs `key`, `name`, `category`, `auth_type` ('oauth'|'api_key'|'aws_role'|'service_account'), `config_schema` (list of field dicts used to render the connect form); methods `validate(creds, config) -> (ok, msg)`, `fetch(ctx) -> iterable[ResourceDict]`, `normalized_types`, `tests` (list of TestDefinition). `ctx` carries org_id, decrypted credentials, config, a rate-limited `requests.Session`, and `last_cursor`.
- `registry.py`: `CONNECTORS = {key: cls}`; `@register` decorator.
- `secrets.py`: Fernet encryption (add `cryptography` to requirements). Key from env `MIGRC_SECRETS_KEY` (separate from SECRET_KEY; support a comma list via `MultiFernet` for rotation). `encrypt_json(dict)`/`decrypt_json(str)`. Never log or render credentials; show only last-4 hints. Also migrate `GoogleWorkspaceConnection` tokens to this (one-off Alembic data migration).
- `sync.py`: `sync_connection(conn)`: decrypt, call `fetch`, upsert `IntegrationResource` by (connection_id, resource_type, external_id), set `last_seen_at`; mark not-seen resources `deleted_at`; project selected types into `Asset`/`Employee`/`EmployeeAccess`; then run tests; record `IntegrationSyncRun`. Wrapped per connection in try/except; failures set `conn.status='error'` + `last_error` and raise a Notification, never abort other orgs.
- `tests/framework.py`: `@test_def(key, title, connector, resource_types, severity, framework_hints, remediation_md)` decorating a function `(resources, config) -> list[Result(resource_id, passed, detail)]`. Pure functions over normalized rows, so they unit-test without network. Test runner stores results and history, then maps to controls and evidence.
- CLI: extend `run_daily_jobs_for_org` to call `sync_all_connections_for_org(org)` and `run_tests_for_org(org)` after snapshots (snapshots must run last so compliance % reflects new results). Add `flask sync-integrations [--org N] [--connector key]` and `flask run-tests`. Respect `sync_interval_hours` (default 24, matches Scrut) so frequent cron is fine. Exit non-zero if any sync failed (existing behaviour).
- Control mapping: tests map to controls by control code across frameworks. Because Control rows are shared per framework, store mapping as `AutomatedTestControl(test_key, control_id)` seeded by `scripts/seed_test_mappings.py` from a YAML (`test_key -> {SOC2: [CC6.1,...], ISO27001: [A.8.5,...]}`), additive/idempotent like seed-frameworks.
- Evidence: on each test run create/refresh one `Evidence` row per (org, test) with `source_type='automated'`, content = JSON/CSV snapshot of results written to `uploads/auto/<org>/...`, `audit_period_*` = run date, auto-status 'Approved' when passing, and an `EvidenceMapping` per mapped control. Keep historical files (retention) so auditors get point-in-time proof.
- ControlStatus rollup: new function `control_auto_status(org, control)`: if the control has any linked tests and all non-ignored are passing -> eligible 'Compliant'; any failing -> 'Non-Compliant' flag (do not overwrite a manual status silently; add `ControlStatus.auto_status` column and let UI show "Automated: failing (3)"). Matches Scrut's rule (all linked items Passing).

### 3.2 Data model (new tables, all with organization_id and indexes on (organization_id, ...))
- `integration_connections`: id, organization_id, connector_key, name (nickname, allows multiple accounts), status (pending|active|error|disabled), credentials_enc (Text, Fernet), config_json (scope: regions, repos, tag filters), sync_interval_hours, last_synced_at, last_success_at, last_error, created_by_id, created_at. Unique (organization_id, connector_key, name).
- `integration_resources`: id, organization_id, connection_id, resource_type (normalized: 'cloud.compute', 'cloud.storage', 'cloud.iam_user', 'identity.user', 'repo', 'repo.branch_protection', 'device', 'ticket'...), external_id, name, region, attributes_json (normalized + raw subset), first_seen_at, last_seen_at, deleted_at. Unique (connection_id, resource_type, external_id).
- `integration_sync_runs`: id, connection_id, started_at, finished_at, status, resource_counts_json, error.
- `automated_tests`: id, key (unique), connector_key, title, description, severity, remediation_md, resource_types_json, enabled_default.
- `automated_test_controls`: test_id, control_id (unique pair).
- `org_test_settings`: organization_id, test_id, ignored (bool), ignored_reason, ignored_by_id, assignee_user_id.
- `test_runs`: id, organization_id, test_id, connection_id, run_at, status (passing|failing|error|not_applicable), total, failed, evidence_id (FK nullable).
- `test_run_resources`: test_run_id, resource_id (FK integration_resources), passed, detail. (Flagged resources table; prune older than 400 days.)
- `Asset` additions: `source` ('manual'|connector key), `external_id`, `connection_id`, `last_seen_at`, `attributes_json`; unique (organization_id, source, external_id). Manual rows untouched.
- `Employee` additions: `external_ids_json`, `mfa_enabled`, `last_login_at`, `is_admin`, `device_encrypted`, `screen_lock`, `av_present`, `last_checkin_at` (replace manual booleans with derived values when a source supplies them).
- `EmployeeAccess`: add nullable `integration_connection_id`, `app_name`, `external_account_id` so SaaS/IdP app assignments can exist without a Vendor.
- Later: `vulnerability_findings` (connection_id, resource_id, cve, severity, status, first_seen, fixed_at) for Dependabot/Inspector.

### 3.3 Files, routes, templates
- `app/connectors/{__init__,base,registry,secrets,sync}.py`, one module per connector (`aws.py`, `github.py`, `googleworkspace.py`, `okta.py`, `slack.py`, `jira.py`, `azure.py`, `gcp.py`), `app/connectors/tests/<connector>_tests.py`.
- `app/routes/integrations.py` (rewrite): `GET /integrations` (catalog from registry + connection cards with status/last sync), `GET/POST /integrations/<key>/connect` (generic form from `config_schema`), `POST /integrations/<id>/sync` (sync now), `POST /integrations/<id>/disconnect`, `POST /integrations/<id>/scope`. Keep `/integrations/google/*` OAuth routes, rework to the base class. Permission: `require_permission('write')`; connect needs admin.
- `app/routes/tests.py` (new blueprint): `GET /tests` (status cards Passing/Fix Required/Ignored, filter by connector/framework/mapping), `GET /tests/<key>` (detail: frameworks, controls, remediation, flagged resources, history sparkline, assignee), `POST /tests/<key>/run` (Test Now, rate-limited), `POST /tests/<key>/ignore`, `/assign`, `GET /tests/<key>/export.csv`.
- Templates: `integrations.html` (rewrite), `integration_connect.html`, `tests.html`, `test_detail.html`; extend `assets.html` with source column, last seen, "discovered" badge, read-only for synced rows; add control page panel "Automated tests" in the existing control detail template; dashboard tile "Tests failing".
- Alerts: on pass->fail transition create `Notification` (existing service) and optional Slack webhook message.
- Tests: `test_connectors_*.py` with recorded fixtures (no network) plus `test_tenant_isolation.py` additions (every new table filtered by org).
- Migrations: one Alembic revision for tables above; separate data migration encrypting Google tokens.

### 3.4 Connector build order, auth, calls, tests

Effort legend: S = <=2 days, M = 3-6 days, L = 1-2 weeks. All tests are pure functions over normalized resources; "FAIL" lists the failing condition. Owner credentials listed per connector.

#### Phase 0 (M): foundation - secrets, tables, base class, sync runner, run-daily-jobs hook, /integrations and /tests UI, evidence+control mapping, Google token migration. Everything else depends on it. Needs owner: generate `MIGRC_SECRETS_KEY` (`python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"`).

#### 1. Google Workspace extension (S-M) - highest value/lowest risk; OAuth already exists
- Auth: existing OAuth web flow; add scopes `admin.directory.user.readonly` (have), `admin.directory.group.readonly`, `admin.directory.device.mobile.readonly`, `admin.reports.audit.readonly`, `admin.directory.domain.readonly`. Requires super-admin consent; owner's Google Cloud OAuth client must have Admin SDK API enabled (free). Existing GOOGLE_CLIENT_ID/SECRET reused; re-consent needed.
- Calls: `directory_v1 users.list` (projection=full gives isEnrolledIn2Sv, isEnforcedIn2Sv, isAdmin, lastLoginTime, suspended, creationTime, archived, orgUnitPath), `groups.list`, `members.list`, `mobiledevices.list`, `reports_v1 activities.list(applicationName='login')`.
- Tests (14): 1) all active users have 2SV enrolled (FAIL per user without isEnrolledIn2Sv); 2) 2SV enforced at org (any isEnforcedIn2Sv false); 3) super admins <= 4; 4) every super admin has 2SV; 5) suspended users still in groups (FAIL if suspended user is member); 6) inactive users >90 days (lastLoginTime); 7) users never logged in >14 days after creation; 8) offboarded employee (Employee.offboarded_at set) still active in Workspace; 9) active Workspace user missing from Employee list; 10) Workspace employee with no department/OU; 11) mobile devices not encrypted (encryptionStatus != ENCRYPTED); 12) mobile devices without screen lock/passcode; 13) mobile devices not synced in 30 days; 14) generic mailbox/admin accounts shared (name heuristics, advisory); 15) no external-domain members in admin groups.
- Data: identity.user, identity.group, device resources -> Employee flags, Asset 'Identity Users/Groups/Mobile Devices'.
- Controls: SOC2 CC6.1-CC6.3, ISO A.5.15-A.5.18, A.8.5; offboarding tests CC6.2/A.6.5.

#### 2. GitHub (M) - free, simplest auth, strong evidence story
- Auth: GitHub App (preferred; read-only, org-installable) OR fine-grained PAT stored encrypted (simplest MVP: PAT with read-only Administration, Metadata, Contents, Pull requests, Dependabot alerts, Secret scanning alerts). Owner supplies a PAT or creates a GitHub App (free).
- Calls (REST v3, paginate, honor rate-limit headers): `GET /orgs/{org}/repos`, `GET /repos/{r}/branches/{default}/protection` (404 = none), `GET /repos/{r}/rulesets`, `GET /orgs/{org}/members?filter=2fa_disabled`, `GET /orgs/{org}/members?role=admin`, `GET /orgs/{org}/outside_collaborators`, `GET /repos/{r}/pulls?state=closed` + `/pulls/{n}/reviews`, `GET /repos/{r}/dependabot/alerts?state=open`, `GET /repos/{r}/secret-scanning/alerts`, `GET /repos/{r}/code-scanning/alerts`, `GET /repos/{r}/collaborators`, `GET /repos/{r}/vulnerability-alerts` (204 enabled), `GET /repos/{r}/contents/.github/CODEOWNERS`, `GET /orgs/{org}/hooks`.
- Tests (16): 1) default branch protected; 2) required PR reviews >=1; 3) dismiss stale reviews; 4) required status checks; 5) force pushes disabled; 6) admins cannot bypass (enforce_admins); 7) org 2FA required (two_factor_requirement_enabled); 8) no members with 2FA disabled; 9) admin count <=5; 10) outside collaborators reviewed (none stale/unknown); 11) PRs merged in last 90d had >=1 approval by non-author (code review results evidence); 12) no direct pushes to default branch (commits without PR, advisory); 13) Dependabot alerts enabled; 14) no open critical/high Dependabot alerts older than 30 days; 15) secret scanning enabled and 0 open alerts; 16) code scanning configured; 17) CODEOWNERS present; 18) private repos only (no public repos with non-allowlisted names); 19) offboarded employees not org members.
- Data: repo, repo.branch_protection, identity.user -> Asset 'Code Repo', vulnerability_findings.
- Controls: SOC2 CC8.1, CC6.1, CC7.1; ISO A.8.25-A.8.32, A.8.4; PR review evidence.

#### 3. AWS (L) - biggest asset/test value; Scrut's flagship
- Auth: customer-side role. Provide a CloudFormation template (shipped in `static/aws/migrc-role.yaml`) creating role `MIGRCReadOnly` with SecurityAudit + ReadOnlyAccess (same as Scrut) and a trust policy to the MIGRC host's AWS principal with `ExternalId` = per-connection random value (confused-deputy protection). For a self-hosted MIGRC the trust principal is the IAM user/role the server runs as; alternative: store a read-only access key pair (encrypted) for simple setups. Calls via `boto3` (add to requirements): `sts.assume_role(ExternalId)`; one session per region.
- Calls: IAM `get_account_summary`, `get_credential_report`, `get_account_password_policy`, `list_users/list_mfa_devices/list_access_keys`, `list_attached_user_policies`; EC2 `describe_instances`, `describe_security_groups`, `describe_volumes`, `describe_vpcs`, `describe_flow_logs`, `describe_snapshots(OwnerIds=self)`, `get_ebs_encryption_by_default`; S3 `list_buckets`, `get_public_access_block`, `get_bucket_encryption`, `get_bucket_versioning`, `get_bucket_logging`, `get_bucket_policy_status`; RDS `describe_db_instances`; CloudTrail `describe_trails`, `get_trail_status`; KMS `list_keys`, `get_key_rotation_status`; GuardDuty `list_detectors`; Config `describe_configuration_recorders`; ELB `describe_load_balancers/listeners`; Lambda `list_functions`; EKS `list_clusters`; CloudWatch `describe_alarms`; Backup `list_backup_plans`; Security Hub/Inspector findings (phase 2).
- Tests (20): 1) root account MFA enabled; 2) root has no access keys; 3) root not used in 90d; 4) all console IAM users have MFA; 5) access keys rotated <=90d; 6) unused credentials >45 days disabled; 7) password policy min length >=14 and reuse prevention; 8) no IAM policies with `*:*` attached to users; 9) IAM users get permissions via groups/roles only (advisory); 10) no security group allows 0.0.0.0/0 on 22/3389; 11) no security group allows 0.0.0.0/0 to all ports; 12) default SG restricts all traffic; 13) EBS default encryption on; 14) all EBS volumes encrypted; 15) VPC flow logs enabled on every VPC; 16) S3 account-level public access block on; 17) no public S3 buckets (policy status / ACL); 18) S3 default encryption on; 19) S3 versioning on for buckets tagged sensitive (config); 20) S3 requires TLS (policy deny aws:SecureTransport false); 21) RDS storage encrypted; 22) RDS not publicly accessible; 23) RDS backup retention >=7d and multi-AZ for prod tag; 24) CloudTrail multi-region trail enabled and logging; 25) CloudTrail log file validation; 26) CMK rotation enabled; 27) GuardDuty enabled per region; 28) AWS Config recorder on; 29) ELB listeners use HTTPS/TLS>=1.2; 30) EC2 IMDSv2 required.
  Ship a first cut of ~20 (these map to CIS AWS Foundations v1.4/3.0 sections 1-5, which is the same CIS basis Scrut cites).
- Data: cloud.compute, cloud.storage, cloud.db, cloud.network, cloud.iam_user/role, cloud.kms, cloud.serverless, cloud.logging -> Asset types already in `ASSET_TYPES`.
- Controls: SOC2 CC6.1, CC6.6, CC6.7, CC7.1-7.2, A1.2; ISO A.8.9, A.8.15, A.8.20, A.8.24.
- Owner needs: an AWS account, run the CF stack, give role ARN (+ the ExternalId MIGRC displays). Free (read APIs are free; Config/GuardDuty are not required).

#### 4. Okta (M)
- Auth: API token (SSWS) from a read-only admin account (Okta "Read-only administrator" role) OR OAuth 2.0 service app with `okta.users.read okta.groups.read okta.apps.read okta.policies.read okta.logs.read`. Free developer tenant (developer.okta.com) available for testing. Owner supplies org URL + token.
- Calls: `GET /api/v1/users?limit=200` (status, lastLogin, created), `/users/{id}/factors`, `/api/v1/groups`, `/api/v1/apps` + `/apps/{id}/users`, `/api/v1/policies?type=OKTA_SIGN_ON|ACCESS_POLICY|PASSWORD|MFA_ENROLL`, `/policies/{id}/rules`, `/api/v1/logs?filter=eventType eq "user.session.start"`, `/api/v1/iam/roles`, `/api/v1/users/{id}/roles`.
- Tests (14): 1) all active users enrolled in MFA; 2) MFA enrollment policy requires MFA; 3) phishing-resistant factor for admins (WebAuthn/Okta Verify FastPass); 4) super admin count <=3; 5) admins have MFA; 6) password policy length >=12 and lockout threshold <=10; 7) password max age/history set; 8) sign-on policy session lifetime <=12h and idle <=2h; 9) inactive users >90d still ACTIVE; 10) DEPROVISIONED/suspended users without app access; 11) offboarded Employee still active in Okta; 12) active Okta user missing from employee list; 13) apps without MFA-enforcing policy; 14) user count with app assignment drift (EmployeeAccess); 15) failed login brute-force spikes (logs, advisory).
- Data: identity.user, identity.group, identity.app_assignment -> Employee (source 'Okta'), EmployeeAccess (app assignments, powers Access Reviews).
- Controls: SOC2 CC6.1-CC6.3; ISO A.5.15-A.5.18, A.8.2, A.8.5.

#### 5. Slack (S) - notifications first, then compliance tests
- Auth (notify): Incoming Webhook URL (stored encrypted) for alerts - S effort, no OAuth. Auth (tests): Slack app OAuth with `users:read users:read.email team:read`, `admin.*` needs Enterprise Grid (paid) so 2FA/SSO tests are limited.
- Calls: `team.info`, `users.list` (has_2fa, is_admin, is_owner, deleted), `chat.postMessage`/webhook for alerts.
- Tests (6): 1) all active members have 2FA (`has_2fa`, available to admins on paid plans; treat missing field as N/A); 2) owners/admins <=5; 3) deactivated vs offboarded mismatch; 4) offboarded employee still active; 5) guest accounts count/stale review (advisory); 6) active member not in employee list.
- Primary value: alerting on test pass->fail, overdue tasks, new incidents. Owner supplies webhook URL.

#### 6. Jira (M)
- Auth: Jira Cloud API token + email (basic auth, stored encrypted) or OAuth 2.0 3LO; free Jira plan (10 users) for testing. Owner supplies site URL, email, token, project key.
- Calls: `POST /rest/api/3/issue` (create from failing test / risk treatment / audit finding / remediation), `GET /rest/api/3/issue/{key}` and `search/jql` to sync status, webhook or poll; `GET /rest/api/3/project`.
- Data: `external_tickets` table (org, entity_type, entity_id, connector, external_key, url, status, last_synced_at). Two-way: when Jira issue moves to Done, mark linked Remediation 'Completed' and queue a test re-run.
- Tests (6, process/evidence-oriented): 1) every High/Critical risk has a linked open/done ticket; 2) critical findings tickets resolved within SLA (e.g. 30d); 3) change-management evidence: issues of type Change with approvals (config); 4) incident tickets closed with postmortem label; 5) backlog of Security-labelled bugs older than SLA; 6) offboarding tickets exist for each departure (config label).
- Controls: SOC2 CC3.x, CC7.4, CC8.1; ISO A.8.32, A.5.24-A.5.27.

#### 7. Azure / Entra ID (M-L) and 8. GCP (M-L)
- Azure: App registration (client credentials) with Reader + Security Reader RBAC at subscription scope and Microsoft Graph application permissions `User.Read.All`, `Directory.Read.All`, `Policy.Read.All`, `AuditLog.Read.All`, `UserAuthenticationMethod.Read.All`. Use `azure-identity` + `azure-mgmt-*` or plain REST (cheaper deps). Calls: Graph `/users`, `/reports/authenticationMethods/userRegistrationDetails`, `/identity/conditionalAccess/policies`, `/directoryRoles`; ARM `Microsoft.Storage/storageAccounts`, `Network/networkSecurityGroups`, `Compute/virtualMachines`, `Sql/servers`, `KeyVault/vaults`, `Security/assessments` (Defender CSPM free tier). Tests (~15): MFA registered for all users, CA policy requires MFA for admins, legacy auth blocked, global admins <=5, storage secure transfer required, no public blob containers, storage encryption/min TLS 1.2, NSG no 0.0.0.0/0 on 22/3389, VM disk encryption, SQL auditing and TDE, Key Vault soft-delete/purge-protection, activity log retention, guest users reviewed, inactive users. Owner supplies tenant ID, client ID/secret, subscription ID.
- GCP: Service account with Viewer + Security Reviewer + Cloud Asset Viewer, JSON key (encrypted) or Workload Identity if self-host on GCP. Calls: Cloud Asset `searchAllResources`, Resource Manager IAM `getIamPolicy`, Compute firewalls/instances/disks, Storage buckets (IAM, uniform access, public), Cloud SQL instances, Logging sinks, KMS key rotation, Org policies. Tests (~15): no primary roles (owner/editor) on user accounts, SA keys rotated <=90d, no user-managed SA keys (advisory), firewall no 0.0.0.0/0 on 22/3389, default network removed, buckets not public/uniform access, Cloud SQL not public/SSL required/backups, disks CMEK/encrypted, VPC flow logs, audit logs enabled for all services, KMS rotation <=365d, OS Login enabled. Owner supplies project ID(s) and key JSON.
- Both reuse the same cloud resource types so the Assets UI needs no change.

#### Later (priority order after the above)
HRIS (BambooHR API key, Gusto/Rippling/Personio; S each, gives hire/exit dates for offboarding tests); Intune/Jamf/Kandji/Fleet (MDM; Fleet and Kandji are the friendliest APIs; M each; fills Employee device flags); Dependabot/Snyk/Trivy ingestion into vulnerability_findings; GitLab/Bitbucket (clone GitHub tests); Cloudflare; Microsoft 365/Google Drive policy sync; Checkr; KnowBe4.

### 3.5 Endpoint/device agent - realistic view
Scrut's agent is osquery-based and checks disk encryption, screen lock, antivirus; it reports every 3 h and is not an MDM replacement. For MIGRC:
- Do NOT build a proprietary signed multi-OS installer early; it needs code signing certificates, update channel, per-OS packaging (pkg/msi/deb), device identity and enrolment security, and ongoing support. That is L to XL and is the highest-maintenance item.
- Pragmatic path in priority order: (1) consume MDM data (Fleet is open source and osquery-based, free, has a REST API: `GET /api/v1/fleet/hosts`, with disk_encryption_enabled, and policy results; Kandji/Jamf/Intune later), which gives Scrut-equivalent device checks; (2) Google Workspace mobile/endpoint data (above) for Workspace shops; (3) if the owner still wants an agent: a thin MIGRC reporter, i.e. documented osquery query pack plus a ~100-line signed script (shell/PowerShell) that POSTs a JSON device check (encryption, screen-lock timeout, AV/firewall, OS version, hostname, serial) with a per-employee enrolment token to `POST /api/agent/checkin`. New table `device_checkins` (employee_id, serial, os, encrypted, screen_lock, av, firewall, os_patch_age, reported_at); a device is stale after 24 h. Effort M for the endpoint plus script, L if packaged installers are added. Honest caveat: self-reported scripts are tamperable; label evidence accordingly.
Recommendation: ship Fleet/MDM ingestion plus the check-in script; defer a native agent.

### 3.6 Owner dependencies summary
- Phase 0: MIGRC_SECRETS_KEY env var (and back it up; losing it orphans all stored credentials).
- Google: re-consent with new scopes; Admin SDK + Admin Reports APIs enabled in the existing Google Cloud project.
- GitHub: PAT or GitHub App. AWS: CF stack run and role ARN; a principal for trust. Okta: org URL + read-only token (dev tenant is free). Slack: webhook URL. Jira: site, email, API token. Azure: app registration. GCP: service-account JSON.
- Public deployment note: OAuth redirect URIs must match the production domain; webhook-based sync (GitHub/Jira) needs a public HTTPS endpoint, otherwise polling in run-daily-jobs.

### 3.7 Suggested sequencing and effort
Phase 0 M -> Google ext S-M -> GitHub M -> AWS L -> Okta M -> Slack S -> Jira M -> MDM/Fleet M -> Azure L -> GCP L -> HRIS S each. Total to reach credible core parity (cloud + IdP + code + ticketing + comms + devices): roughly 8-10 engineering weeks. Reaching about 40% section parity after AWS + GitHub + Google + Okta; about 60% once Jira/Slack/MDM/Azure/GCP are added. The remaining long tail (150+ SaaS tiles) is not worth pursuing; offer a generic "webhook/CSV/API evidence ingest" connector (S) instead, which covers the custom-integration gap reviewers complain about.

### 3.8 Security requirements for the new code
Encrypt credentials at rest (Fernet); least privilege and read-only scopes only; per-connection ExternalId for AWS; SSRF guard on user-supplied base URLs (Okta/Jira/Fleet: https only, block private IP ranges unless explicitly allowed for self-hosted Fleet); never return credentials to templates; audit-log connect/disconnect via `log_activity`; all queries filtered by organization_id (extend test_tenant_isolation); timeouts and retries with backoff on every HTTP call; truncate stored raw payloads to avoid storing secrets or PII beyond what tests need.
