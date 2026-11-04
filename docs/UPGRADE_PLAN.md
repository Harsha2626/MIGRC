# MIGRC Upgrade Plan

Source: code-review + security audit + Scrut feature-gap analysis (2026-11-04).

## Phase 1 (parallel, isolated worktrees)
| Stream | Scope |
|---|---|
| SEC | Fix cross-tenant EvidenceMapping IDOR + `map_control_ids` injection (add `organization_id`, migration, visibility validation); CSV formula-injection escaping; session cookie flags; `OAUTHLIB_INSECURE_TRANSPORT` default; login rate limiting; ActivityLog org scoping; assignee/approver org-membership checks; migration backfill bug; `add_framework` IntegrityError; setup wizard ordering; remove dead `OrganizationExcludedFramework`; N+1 framework counts; IDOR regression tests |
| AI | Run AI through the running OpenCode server (unpin Cline); harden dispatch; AI questionnaire-answer assist for vendors; AI evidence review/policy eval kept human-in-the-loop; docs |
| FEAT | Flask CLI for scheduled jobs (daily snapshots, deadline/stale-evidence notifications) so automation no longer depends on page loads; honest Integrations page (real status, no fake buttons); framework library seeding command |
| DESIGN | Design system rewrite: `static/css/style.css`, `base.html`, `dashboard.html`, `login.html` |

## Phase 2 (after merge)
- UI/UX rollout across remaining templates in parallel batches (compliance/controls/tests, policies/audits, risks/vendors/assets, people/training/settings/setup/trust center/reports).
- Incident management module (model + migration + routes + templates).

## Phase 3 (needs credentials / product decisions)
- AWS integration (boto3 + Security Hub/Config) with automated control checks.
- Auditor portal (external read-only collaborator role).
- Billing/plans.
