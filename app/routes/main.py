from datetime import date, timedelta
from flask import Blueprint, render_template, jsonify, request, Response, session, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required
from app.models import (
    db, Framework, Risk, Policy, Audit, Vendor, Asset, Control, User,
    Evidence, ComplianceSnapshot, DashboardSnapshot, ActivityLog, TrainingCampaign, NDAAcceptance,
)
from app.services.snapshots import ensure_snapshots_for_today
from app.services.notifications import ensure_notifications_for_today
from app.services.pdf_reports import build_dashboard_snapshot_pdf, build_policy_document_pdf, build_trust_certificate_pdf
from app.services.csv_export import csv_response
from app.services.badge import build_badge_svg
from app.utils import parse_date_safe
from app.routes.risks import RISK_LEVEL_SCORES

main_bp = Blueprint('main', __name__)

RISK_LEVELS = ['Negligible', 'Low', 'Medium', 'High', 'Critical']


def _weighted_compliance_score(frameworks):
    """Overall score = Passing / (Total - N/A) x 100, weighted across frameworks by applicable controls."""
    total_applicable = 0
    weighted_sum = 0.0
    for fw in frameworks:
        applicable = fw.total_controls - fw.not_applicable
        total_applicable += applicable
        weighted_sum += fw.compliance_score * applicable
    if total_applicable == 0:
        return 0
    return round(weighted_sum / total_applicable)


def _dashboard_context():
    frameworks = Framework.query.all()
    framework_dicts = [fw.to_dict() for fw in frameworks]

    total_controls = sum(fw.total_controls for fw in frameworks)
    passing_controls = sum(fw.passing for fw in frameworks)
    failing_controls = sum(fw.failing for fw in frameworks)
    na_controls = sum(fw.not_applicable for fw in frameworks)
    compliance_score = _weighted_compliance_score(frameworks)

    risks = Risk.query.all()
    open_risks = len([r for r in risks if r.status == 'Open'])
    critical_risks = len([r for r in risks if r.impact == 'Critical'])

    policy_count = Policy.query.filter_by(status='Published').count()
    audits = Audit.query.all()
    pending_audits = len([a for a in audits if a.status in ['In Progress', 'Scheduled']])
    pending_evidence = Evidence.query.filter_by(status='Pending Review').count()

    return dict(
        compliance_score=compliance_score,
        total_controls=total_controls,
        passing_controls=passing_controls,
        failing_controls=failing_controls,
        na_controls=na_controls,
        open_risks=open_risks,
        critical_risks=critical_risks,
        policy_count=policy_count,
        pending_evidence=pending_evidence,
        pending_audits=pending_audits,
        frameworks=framework_dicts,
        risks=risks[:5],
        audits=audits,
        vendors_count=Vendor.query.count(),
        assets_count=Asset.query.count(),
        kpis=_build_kpis(compliance_score, open_risks, policy_count, pending_evidence),
        risk_levels=RISK_LEVELS,
        risk_level_scores=RISK_LEVEL_SCORES,
        risk_matrix=_build_risk_matrix(risks),
        deadlines=_build_upcoming_deadlines(),
    )


@main_bp.route('/')
@login_required
def dashboard():
    ensure_snapshots_for_today()
    ensure_notifications_for_today()

    context = _dashboard_context()
    trend_labels, trend_data = _build_compliance_trend()
    recent_activity = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(20).all()

    return render_template('dashboard.html',
        page='dashboard',
        trend_labels=trend_labels,
        trend_data=trend_data,
        recent_activity=recent_activity,
        **context,
    )


def _closest_snapshot_on_or_before(model, cutoff_date):
    """Most recent snapshot dated <= cutoff, falling back to the oldest snapshot at all."""
    row = model.query.filter(model.snapshot_date <= cutoff_date).order_by(model.snapshot_date.desc()).first()
    if row:
        return row
    return model.query.order_by(model.snapshot_date.asc()).first()


def _build_kpis(compliance_score, open_risks, policy_count, pending_evidence):
    week_ago = date.today() - timedelta(days=7)

    old_dashboard = _closest_snapshot_on_or_before(DashboardSnapshot, week_ago)

    old_compliance_row = _closest_snapshot_on_or_before(ComplianceSnapshot, week_ago)
    old_compliance_score = None
    if old_compliance_row:
        peers = ComplianceSnapshot.query.filter_by(snapshot_date=old_compliance_row.snapshot_date).all()
        old_applicable = sum(s.total_controls - s.not_applicable for s in peers)
        old_passing = sum(s.passing for s in peers)
        old_compliance_score = round((old_passing / old_applicable) * 100) if old_applicable else 0

    kpis = [
        dict(label='Compliance Score', value=f'{compliance_score}%', icon='fa-shield-halved', color='blue',
             delta=None if old_compliance_score is None else compliance_score - old_compliance_score,
             good_when='up'),
        dict(label='Open Risks', value=open_risks, icon='fa-triangle-exclamation', color='red',
             delta=None if not old_dashboard else open_risks - old_dashboard.open_risks,
             good_when='down'),
        dict(label='Active Policies', value=policy_count, icon='fa-file-shield', color='purple',
             delta=None if not old_dashboard else policy_count - old_dashboard.active_policies,
             good_when='up'),
        dict(label='Pending Evidence', value=pending_evidence, icon='fa-clock', color='orange',
             delta=None if not old_dashboard else pending_evidence - old_dashboard.pending_evidence,
             good_when='down'),
    ]

    for kpi in kpis:
        if kpi['delta'] is None:
            kpi['direction'] = None
            kpi['is_good'] = None
        elif kpi['delta'] == 0:
            kpi['direction'] = 'flat'
            kpi['is_good'] = True
        else:
            kpi['direction'] = 'up' if kpi['delta'] > 0 else 'down'
            kpi['is_good'] = kpi['direction'] == kpi['good_when']

    return kpis


def _build_risk_matrix(risks):
    matrix = {l: {i: 0 for i in RISK_LEVELS} for l in RISK_LEVELS}
    for r in risks:
        if r.likelihood in matrix and r.impact in matrix[r.likelihood]:
            matrix[r.likelihood][r.impact] += 1
    return matrix


def _build_compliance_trend():
    start = date.today() - timedelta(days=30)
    snaps = (ComplianceSnapshot.query
        .filter(ComplianceSnapshot.snapshot_date >= start)
        .order_by(ComplianceSnapshot.snapshot_date)
        .all())

    by_date = {}
    for s in snaps:
        by_date.setdefault(s.snapshot_date, []).append(s)

    labels, data = [], []
    for d in sorted(by_date.keys()):
        peers = by_date[d]
        applicable = sum(s.total_controls - s.not_applicable for s in peers)
        passing = sum(s.passing for s in peers)
        labels.append(d.strftime('%d %b'))
        data.append(round((passing / applicable) * 100) if applicable else 0)

    return labels, data


def _build_upcoming_deadlines():
    today = date.today()
    horizon = today + timedelta(days=30)
    deadlines = []

    for p in Policy.query.all():
        d = parse_date_safe(p.next_review)
        if d and today <= d <= horizon:
            deadlines.append({'type': 'Policy Review', 'icon': 'fa-file-shield', 'name': p.name, 'date': d})

    for v in Vendor.query.all():
        d = parse_date_safe(v.next_assessment)
        if d and today <= d <= horizon:
            deadlines.append({'type': 'Vendor Assessment', 'icon': 'fa-building', 'name': v.name, 'date': d})

    for a in Audit.query.filter(Audit.status != 'Completed').all():
        start_d = parse_date_safe(a.start_date)
        end_d = parse_date_safe(a.end_date)
        if start_d and today <= start_d <= horizon:
            deadlines.append({'type': 'Audit Starts', 'icon': 'fa-magnifying-glass-chart', 'name': a.name, 'date': start_d})
        elif end_d and today <= end_d <= horizon:
            deadlines.append({'type': 'Audit Ends', 'icon': 'fa-magnifying-glass-chart', 'name': a.name, 'date': end_d})

    for t in TrainingCampaign.query.filter(TrainingCampaign.status != 'Completed').all():
        d = parse_date_safe(t.end_date)
        if d and today <= d <= horizon:
            deadlines.append({'type': 'Training Ends', 'icon': 'fa-graduation-cap', 'name': t.name, 'date': d})

    deadlines.sort(key=lambda x: x['date'])
    for dl in deadlines:
        days_until = (dl['date'] - today).days
        dl['days_until'] = days_until
        dl['urgency'] = 'red' if days_until <= 7 else ('orange' if days_until <= 14 else 'gray')

    return deadlines[:10]


@main_bp.route('/trust-center')
def trust_center():
    published_policies = Policy.query.filter_by(status='Published').all()
    active_frameworks = Framework.query.all()
    overall_score = _weighted_compliance_score(active_frameworks)
    return render_template('trust_center.html', page='trust_center',
        policies=published_policies, frameworks=[fw.to_dict() for fw in active_frameworks],
        overall_score=overall_score, nda_accepted=session.get('nda_accepted', False))


@main_bp.route('/trust-center/nda-accept', methods=['POST'])
def trust_center_nda_accept():
    email = request.form.get('email', '').strip().lower()
    name = request.form.get('name', '').strip()
    company = request.form.get('company', '').strip()
    policy_id = request.form.get('policy_id', type=int)

    if not email:
        flash('Email is required to accept the NDA.', 'error')
        return redirect(url_for('main.trust_center'))

    db.session.add(NDAAcceptance(email=email, name=name, company=company, ip_address=request.remote_addr))
    db.session.commit()
    session['nda_accepted'] = True

    if policy_id:
        return redirect(url_for('main.trust_center_download', policy_id=policy_id))
    return redirect(url_for('main.trust_center'))


@main_bp.route('/trust-center/download/<int:policy_id>')
def trust_center_download(policy_id):
    if not session.get('nda_accepted'):
        flash('Please accept the NDA to download this document.', 'error')
        return redirect(url_for('main.trust_center'))

    policy = Policy.query.filter_by(id=policy_id, status='Published').first_or_404()

    if policy.content_state == 'file':
        upload_folder = current_app.config['UPLOAD_FOLDER']
        return send_from_directory(upload_folder, policy.file_path, as_attachment=True,
            download_name=policy.file_name or policy.file_path)
    if policy.content_state == 'external':
        return redirect(policy.external_url)

    pdf_bytes = build_policy_document_pdf(policy)
    return Response(pdf_bytes, mimetype='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="{policy.name.replace(" ", "_")}.pdf"'
    })


@main_bp.route('/trust-center/certificate/<int:framework_id>')
def trust_center_certificate(framework_id):
    framework = Framework.query.get_or_404(framework_id)
    pdf_bytes = build_trust_certificate_pdf(framework)
    return Response(pdf_bytes, mimetype='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="{framework.name.replace(" ", "_")}_Attestation.pdf"'
    })


@main_bp.route('/trust-center/badge.svg')
def trust_center_badge():
    framework_id = request.args.get('framework', type=int)
    if framework_id:
        fw = Framework.query.get_or_404(framework_id)
        applicable = fw.total_controls - fw.not_applicable
        score = round((fw.passing / applicable) * 100) if applicable else 0
        label = fw.name
    else:
        label = 'Compliance'
        score = _weighted_compliance_score(Framework.query.all())

    svg = build_badge_svg(label, f'{score}%')
    return Response(svg, mimetype='image/svg+xml', headers={'Cache-Control': 'public, max-age=3600'})


@main_bp.route('/settings')
@login_required
def settings():
    users = User.query.all()
    return render_template('settings.html', page='settings', users=users)


@main_bp.route('/settings/activity-log')
@login_required
def activity_log():
    entity_type = request.args.get('entity_type', '')
    action = request.args.get('action', '')
    user_id = request.args.get('user_id', '')
    page = max(int(request.args.get('page', 1)), 1)
    per_page = 50

    query = ActivityLog.query
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    if action:
        query = query.filter_by(action=action)
    if user_id:
        query = query.filter_by(user_id=int(user_id))
    query = query.order_by(ActivityLog.created_at.desc())

    total = query.count()
    entries = query.offset((page - 1) * per_page).limit(per_page).all()

    entity_types = [row[0] for row in db.session.query(ActivityLog.entity_type).distinct().order_by(ActivityLog.entity_type).all()]
    actions = [row[0] for row in db.session.query(ActivityLog.action).distinct().order_by(ActivityLog.action).all()]
    users = User.query.order_by(User.name).all()

    return render_template('activity_log.html', page='settings',
        entries=entries, total=total, current_page=page, per_page=per_page,
        entity_types=entity_types, actions=actions, users=users,
        selected_entity_type=entity_type, selected_action=action, selected_user_id=user_id)


@main_bp.route('/settings/activity-log/export')
@login_required
def export_activity_log():
    rows = [(e.created_at.strftime('%Y-%m-%d %H:%M:%S') if e.created_at else '', e.user.name if e.user else '-', e.action, e.entity_type, e.entity_name or '', e.description or '')
            for e in ActivityLog.query.order_by(ActivityLog.created_at.desc()).all()]
    return csv_response('activity_log.csv', ['When', 'User', 'Action', 'Entity Type', 'Entity Name', 'Description'], rows)


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
