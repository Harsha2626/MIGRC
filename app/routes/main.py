from datetime import date, timedelta
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from app.models import db, Framework, Risk, Policy, Audit, Vendor, Asset, Control, User, ComplianceSnapshot

main_bp = Blueprint('main', __name__)


def _weighted_compliance_score(frameworks):
    """Overall score = weighted average across frameworks (weight = applicable controls)."""
    total_applicable = 0
    weighted_sum = 0.0
    for fw in frameworks:
        applicable = fw.total_controls - fw.not_applicable
        total_applicable += applicable
        weighted_sum += fw.compliance_score * applicable
    if total_applicable == 0:
        return 0.0
    return round(weighted_sum / total_applicable, 1)


def _score_delta(frameworks):
    """Compare current overall score vs 30 days ago snapshot."""
    thirty_days_ago = date.today() - timedelta(days=30)

    # Get the most recent snapshot on or before 30 days ago for each framework
    old_weighted_sum = 0.0
    old_total_applicable = 0

    for fw in frameworks:
        snapshot = ComplianceSnapshot.query.filter(
            ComplianceSnapshot.framework_id == fw.id,
            ComplianceSnapshot.snapshot_date <= thirty_days_ago
        ).order_by(ComplianceSnapshot.snapshot_date.desc()).first()

        if snapshot:
            applicable = snapshot.total_controls - snapshot.not_applicable
            old_total_applicable += applicable
            old_weighted_sum += snapshot.score * applicable

    if old_total_applicable == 0:
        return None  # No historical data yet

    old_score = old_weighted_sum / old_total_applicable
    current_score = _weighted_compliance_score(frameworks)
    return round(current_score - old_score, 1)


def _compliance_trend_data(frameworks, months=6):
    """Get monthly compliance scores for the trend chart."""
    today = date.today()
    labels = []
    scores = []

    for i in range(months - 1, -1, -1):
        # First day of each month going back
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        month_date = date(y, m, 1)
        # Last day of the month (approximate: use first of next month - 1 day)
        if m == 12:
            end_date = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(y, m + 1, 1) - timedelta(days=1)

        labels.append(month_date.strftime('%b %Y'))

        # Get latest snapshot for each framework in that month
        month_weighted = 0.0
        month_applicable = 0
        for fw in frameworks:
            snapshot = ComplianceSnapshot.query.filter(
                ComplianceSnapshot.framework_id == fw.id,
                ComplianceSnapshot.snapshot_date >= month_date,
                ComplianceSnapshot.snapshot_date <= end_date
            ).order_by(ComplianceSnapshot.snapshot_date.desc()).first()

            if snapshot:
                applicable = snapshot.total_controls - snapshot.not_applicable
                month_applicable += applicable
                month_weighted += snapshot.score * applicable

        if month_applicable > 0:
            scores.append(round(month_weighted / month_applicable, 1))
        else:
            scores.append(None)  # No data for that month

    return labels, scores


@main_bp.route('/')
@login_required
def dashboard():
    frameworks = Framework.query.all()
    framework_dicts = [fw.to_dict() for fw in frameworks]

    total_controls = sum(fw.total_controls for fw in frameworks)
    passing_controls = sum(fw.passing for fw in frameworks)
    failing_controls = sum(fw.failing for fw in frameworks)
    na_controls = sum(fw.not_applicable for fw in frameworks)

    # Weighted compliance score: Passing / (Total - N/A) × 100
    compliance_score = _weighted_compliance_score(frameworks)

    # Delta from 30 days ago
    score_delta = _score_delta(frameworks)

    # Trend data for chart (last 6 months)
    trend_labels, trend_scores = _compliance_trend_data(frameworks, months=6)

    risks = Risk.query.all()
    open_risks = len([r for r in risks if r.status == 'Open'])
    critical_risks = len([r for r in risks if r.impact == 'Critical'])

    policy_count = Policy.query.filter_by(status='Published').count()
    audits = Audit.query.all()
    pending_audits = len([a for a in audits if a.status in ['In Progress', 'Scheduled']])

    return render_template('dashboard.html',
        page='dashboard',
        compliance_score=compliance_score,
        total_controls=total_controls,
        passing_controls=passing_controls,
        failing_controls=failing_controls,
        na_controls=na_controls,
        score_delta=score_delta,
        trend_labels=trend_labels,
        trend_scores=trend_scores,
        open_risks=open_risks,
        critical_risks=critical_risks,
        policy_count=policy_count,
        pending_audits=pending_audits,
        frameworks=framework_dicts,
        risks=risks[:5],
        audits=audits,
        vendors_count=Vendor.query.count(),
        assets_count=Asset.query.count(),
    )


@main_bp.route('/trust-center')
@login_required
def trust_center():
    published_policies = Policy.query.filter_by(status='Published').all()
    active_frameworks = Framework.query.all()
    return render_template('trust_center.html', page='trust_center',
        policies=published_policies, frameworks=[fw.to_dict() for fw in active_frameworks])


@main_bp.route('/settings')
@login_required
def settings():
    users = User.query.all()
    return render_template('settings.html', page='settings', users=users)


# ---- API Endpoints ----

@main_bp.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    frameworks = Framework.query.all()
    total_controls = sum(fw.total_controls for fw in frameworks)
    passing = sum(fw.passing for fw in frameworks)
    failing = sum(fw.failing for fw in frameworks)
    return jsonify({
        'compliance_score': _weighted_compliance_score(frameworks),
        'total_controls': total_controls,
        'passing': passing,
        'failing': failing,
        'open_risks': Risk.query.filter_by(status='Open').count(),
        'critical_risks': Risk.query.filter_by(impact='Critical').count(),
        'frameworks': [fw.to_dict() for fw in frameworks],
    })
