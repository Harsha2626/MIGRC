"""Flask CLI commands for scheduled/maintenance jobs.

    flask run-daily-jobs     snapshots + due/overdue notifications for every organization
    flask seed-frameworks    additively load the shared framework library
    flask jobs-status        show what the jobs have produced

All commands are safe to re-run (idempotent) and exit non-zero on failure so cron/systemd
can alert. See docs/scheduled-jobs.md.
"""
import importlib.util
import sys
import time
from datetime import date
from pathlib import Path

import click
from flask import current_app, g

ROOT = Path(__file__).resolve().parent.parent


def run_daily_jobs_for_org(org):
    """Run the daily jobs for one organization inside an app context.
    Returns (snapshot_rows_created, notifications_created)."""
    from app.services.snapshots import ensure_snapshots_for_today
    from app.services.notifications import ensure_notifications_for_today

    g.current_org = org
    g.current_membership = None
    try:
        snaps = ensure_snapshots_for_today()
        notifs = ensure_notifications_for_today()
    finally:
        g.current_org = None
    return snaps, notifs


def run_daily_jobs():
    """Run daily jobs for every organization. Returns list of (org_id, name, snaps, notifs, error)."""
    from app.models import db, Organization

    results = []
    org_ids = [(o.id, o.name) for o in Organization.query.order_by(Organization.id).all()]
    for org_id, name in org_ids:
        try:
            org = db.session.get(Organization, org_id)
            snaps, notifs = run_daily_jobs_for_org(org)
            results.append((org_id, name, snaps, notifs, None))
        except Exception as exc:  # one broken org must not block the others
            db.session.rollback()
            current_app.logger.exception('daily jobs failed for organization %s', org_id)
            results.append((org_id, name, 0, 0, exc))
    return results


def _load_seeder():
    # scripts/ is not a package; load by path so this works from any cwd (cron).
    spec = importlib.util.spec_from_file_location('seed_frameworks_script', ROOT / 'scripts' / 'seed_frameworks.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def register_cli(app):
    @app.cli.command('run-daily-jobs')
    def run_daily_jobs_command():
        """Create today's snapshots and due/overdue notifications for every organization."""
        started = time.monotonic()
        current_app.logger.info('run-daily-jobs: starting')
        try:
            results = run_daily_jobs()
        except Exception:
            current_app.logger.exception('run-daily-jobs: aborted')
            click.echo('run-daily-jobs: FAILED', err=True)
            sys.exit(1)

        failures = 0
        for org_id, name, snaps, notifs, err in results:
            if err:
                failures += 1
                click.echo(f'org {org_id} ({name}): ERROR {err!r}', err=True)
            else:
                click.echo(f'org {org_id} ({name}): {snaps} snapshot rows, {notifs} notifications created')
        elapsed = time.monotonic() - started
        summary = f'run-daily-jobs: {len(results)} orgs, {failures} failed, {elapsed:.1f}s'
        current_app.logger.info(summary)
        click.echo(summary)
        if failures:
            sys.exit(1)

    @app.cli.command('seed-frameworks')
    def seed_frameworks_command():
        """Additively seed the shared compliance framework library (safe to re-run)."""
        try:
            added, skipped, total = _load_seeder().seed_frameworks_in_context()
        except Exception:
            from app.models import db
            db.session.rollback()
            current_app.logger.exception('seed-frameworks failed')
            click.echo('seed-frameworks: FAILED', err=True)
            sys.exit(1)
        click.echo(f'Added {added} frameworks, skipped {skipped} (already present). Library total: {total}.')

    @app.cli.command('jobs-status')
    def jobs_status_command():
        """Show per-organization snapshot/notification state and framework library size."""
        from sqlalchemy import func
        from app.models import (db, Organization, ComplianceSnapshot, DashboardSnapshot,
                                Notification, Framework)
        today = date.today()
        click.echo(f'Today: {today}')
        click.echo(f'Shared framework library: {Framework.query.filter(Framework.organization_id.is_(None)).count()} frameworks')
        missing = 0
        for org in Organization.query.order_by(Organization.id).all():
            last_dash = db.session.query(func.max(DashboardSnapshot.snapshot_date)).filter_by(organization_id=org.id).scalar()
            last_comp = db.session.query(func.max(ComplianceSnapshot.snapshot_date)).filter_by(organization_id=org.id).scalar()
            last_notif = db.session.query(func.max(Notification.created_at)).filter_by(organization_id=org.id).scalar()
            ok = last_dash == today
            missing += 0 if ok else 1
            click.echo(f'org {org.id} ({org.name}): dashboard snapshot {last_dash or "never"}'
                       f' [{"ok" if ok else "STALE"}], compliance snapshot {last_comp or "never"},'
                       f' last notification {last_notif or "never"}')
        if missing:
            click.echo(f'{missing} organization(s) lack today\'s snapshot - run `flask run-daily-jobs`.')
