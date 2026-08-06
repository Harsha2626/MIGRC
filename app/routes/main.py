from flask import Blueprint, render_template, jsonify
from app.models import db, Framework, Risk, Policy, Audit, Vendor, Asset, Control

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def dashboard():
    frameworks = Framework.query.all()
    framework_dicts = [fw.to_dict() for fw in frameworks]

    total_controls = sum(fw.total_controls for fw in frameworks)
    passing_controls = sum(fw.passing for fw in frameworks)
    failing_controls = sum(fw.failing for fw in frameworks)
    compliance_score = round((passing_controls / total_controls) * 100) if total_controls > 0 else 0

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
def trust_center():
    published_policies = Policy.query.filter_by(status='Published').all()
    active_frameworks = Framework.query.all()
    return render_template('trust_center.html', page='trust_center',
        policies=published_policies, frameworks=[fw.to_dict() for fw in active_frameworks])


@main_bp.route('/settings')
def settings():
    return render_template('settings.html', page='settings')


# ---- API Endpoints ----

@main_bp.route('/api/dashboard/stats')
def api_dashboard_stats():
    frameworks = Framework.query.all()
    total_controls = sum(fw.total_controls for fw in frameworks)
    passing = sum(fw.passing for fw in frameworks)
    failing = sum(fw.failing for fw in frameworks)
    return jsonify({
        'compliance_score': round((passing / total_controls) * 100) if total_controls > 0 else 0,
        'total_controls': total_controls,
        'passing': passing,
        'failing': failing,
        'open_risks': Risk.query.filter_by(status='Open').count(),
        'critical_risks': Risk.query.filter_by(impact='Critical').count(),
        'frameworks': [fw.to_dict() for fw in frameworks],
    })
