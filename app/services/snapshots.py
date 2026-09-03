from datetime import date
from app.models import db, Framework, Risk, Policy, Evidence, ComplianceSnapshot, DashboardSnapshot


def ensure_snapshots_for_today():
    """Idempotently record today's compliance/dashboard/vendor snapshot rows, once per day."""
    today = date.today()

    for framework in Framework.query.all():
        exists = ComplianceSnapshot.query.filter_by(framework_id=framework.id, snapshot_date=today).first()
        if not exists:
            db.session.add(ComplianceSnapshot(
                framework_id=framework.id,
                score=framework.compliance_score,
                passing=framework.passing,
                failing=framework.failing,
                not_assessed=framework.not_assessed,
                not_applicable=framework.not_applicable,
                total_controls=framework.total_controls,
                snapshot_date=today,
            ))

    if not DashboardSnapshot.query.filter_by(snapshot_date=today).first():
        db.session.add(DashboardSnapshot(
            snapshot_date=today,
            open_risks=Risk.query.filter_by(status='Open').count(),
            active_policies=Policy.query.filter_by(status='Published').count(),
            pending_evidence=Evidence.query.filter_by(status='Pending Review').count(),
        ))

    db.session.commit()
