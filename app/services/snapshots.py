from datetime import date
from flask import g
from sqlalchemy.exc import IntegrityError
from app.models import db, Framework, Risk, Policy, Evidence, ComplianceSnapshot, DashboardSnapshot


def ensure_snapshots_for_today():
    """Idempotently record today's compliance/dashboard snapshot rows for the current
    organization (g.current_org), once per day. Used by both the dashboard (on demand) and
    `flask run-daily-jobs`. Race-safe: the unique constraints on the snapshot tables make a
    concurrent insert fail with IntegrityError, which is swallowed. Returns rows created."""
    org = getattr(g, 'current_org', None)
    if not org:
        return 0
    org_id = org.id
    today = date.today()
    created = 0

    # Use no_autoflush so that pending inserts inside the loop don't trigger an
    # autoflush (and a UniqueViolation) when the next SELECT is executed.
    with db.session.no_autoflush:
        # Snapshot progress for every framework this org can see (shared library + their own
        # private ones); framework.compliance_score etc. read g.current_org internally.
        for framework in Framework.visible_to(org_id).all():
            exists = ComplianceSnapshot.query.filter_by(
                organization_id=org_id,
                framework_id=framework.id,
                snapshot_date=today,
            ).first()
            if not exists:
                created += 1
                db.session.add(ComplianceSnapshot(
                    organization_id=org_id,
                    framework_id=framework.id,
                    score=framework.compliance_score,
                    passing=framework.passing,
                    failing=framework.failing,
                    not_assessed=framework.not_assessed,
                    not_applicable=framework.not_applicable,
                    total_controls=framework.total_controls,
                    snapshot_date=today,
                ))

        if not DashboardSnapshot.query.filter_by(organization_id=org_id, snapshot_date=today).first():
            created += 1
            db.session.add(DashboardSnapshot(
                organization_id=org_id,
                snapshot_date=today,
                open_risks=Risk.query.filter_by(organization_id=org_id, status='Open').count(),
                active_policies=Policy.query.filter_by(organization_id=org_id, status='Published').count(),
                pending_evidence=Evidence.query.filter_by(organization_id=org_id, status='Pending Review').count(),
            ))

    try:
        db.session.commit()
    except IntegrityError:
        # Another concurrent request or the CLI daily job already inserted the snapshot.
        db.session.rollback()
        return 0
    return created
