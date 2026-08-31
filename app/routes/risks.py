from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, Risk, RiskTreatment, TreatmentMilestone, Control
from app.services.activity import log_activity
from app.services.notifications import notify_risk_escalated
from app.services.csv_export import csv_response
from app.utils import require_permission

risks_bp = Blueprint('risks', __name__)

RISK_LEVEL_SCORES = {'Critical': 5, 'High': 4, 'Medium': 3, 'Low': 2, 'Negligible': 1}

# Curated library of common risks a team can browse and drop straight into their
# register instead of writing every risk from scratch. Categories match the
# RISK_CATEGORIES options already used on the Add/Edit Risk form.
RISK_CATALOG = [
    {'title': 'Departing Employee Access Retention', 'category': 'Access Control',
     'description': 'Access for employees who have left the organization is not revoked promptly, allowing continued system access after departure.'},
    {'title': 'Weak or Shared Credentials', 'category': 'Access Control',
     'description': 'Use of shared accounts or weak password policies increases the likelihood of unauthorized access to sensitive systems.'},
    {'title': 'Unencrypted Sensitive Data at Rest', 'category': 'Data Protection',
     'description': 'Databases or storage volumes containing sensitive data without encryption increase exposure if the underlying media is lost or compromised.'},
    {'title': 'Cross-Border Data Transfer Non-Compliance', 'category': 'Data Protection',
     'description': 'Transferring personal data across jurisdictions without appropriate safeguards may violate data protection regulations.'},
    {'title': 'Expired or Missing Data Processing Agreements', 'category': 'Vendor Risk',
     'description': 'Working with vendors that process personal data without a current, signed DPA in place creates regulatory exposure.'},
    {'title': 'Unmanaged Shadow IT', 'category': 'Vendor Risk',
     'description': 'Employees adopting unsanctioned SaaS tools outside of procurement and security review introduces unassessed third-party risk.'},
    {'title': 'Misconfigured Cloud Storage Permissions', 'category': 'Cloud Security',
     'description': 'Publicly accessible or overly permissive cloud storage buckets may expose sensitive data to the internet.'},
    {'title': 'Missing Cloud Activity Logging', 'category': 'Cloud Security',
     'description': 'Lack of centralized logging across cloud accounts limits visibility into suspicious or unauthorized activity.'},
    {'title': 'Single Point of Failure in Critical Infrastructure', 'category': 'Business Continuity',
     'description': 'Reliance on a single server, data center, or vendor for a critical service could cause extended downtime if that component fails.'},
    {'title': 'Untested Backup and Recovery Process', 'category': 'Business Continuity',
     'description': 'Backups exist but recovery procedures have not been tested, risking data loss if a restore is required during an actual incident.'},
    {'title': 'Office or Facility Disruption', 'category': 'Business Continuity',
     'description': 'Natural disasters, utility outages, or civil disruption could make primary work locations inaccessible for staff.'},
    {'title': 'Phishing and Social Engineering Campaigns', 'category': 'Social Engineering',
     'description': 'Employees may be targeted by phishing emails or calls designed to steal credentials or install malware.'},
    {'title': 'Impersonation of IT Support', 'category': 'Social Engineering',
     'description': 'Attackers posing as internal IT or helpdesk staff may trick employees into resetting credentials or granting remote access.'},
    {'title': 'Outdated Software and Missing Patches', 'category': 'Vulnerability Mgmt',
     'description': 'Systems running unsupported or unpatched software versions are more susceptible to known, publicly documented exploits.'},
    {'title': 'Unremediated Critical Vulnerabilities', 'category': 'Vulnerability Mgmt',
     'description': 'Critical vulnerabilities identified in scans remain open past their remediation SLA, leaving a known window of exposure.'},
]

TASK_STATUSES = ['Planned', 'In Progress', 'Pending Approval', 'Needs Revision', 'Completed']


def _is_overdue(treatment):
    if treatment.status == 'Completed' or not treatment.deadline:
        return False
    try:
        return datetime.strptime(treatment.deadline, '%Y-%m-%d').date() < date.today()
    except ValueError:
        return False


@risks_bp.route('/risks')
@login_required
def risks():
    all_risks = Risk.query.order_by(Risk.score.desc()).all()
    # Template uses {{ risks|tojson }} for JS risk matrix, so pass dicts
    risk_dicts = [r.to_dict() for r in all_risks]

    all_treatments = RiskTreatment.query.order_by(RiskTreatment.deadline.asc()).all()
    tasks = []
    task_counts = {'open': 0, 'overdue': 0, 'needs_attention': 0, 'completed': 0}
    for t in all_treatments:
        overdue = _is_overdue(t)
        tasks.append({
            'id': t.id, 'risk_id': t.risk_id, 'risk_title': t.risk.title,
            'action': t.action, 'owner': t.owner, 'department': t.department,
            'deadline': t.deadline, 'status': t.status, 'overdue': overdue,
            'treatment_strategy': t.risk.treatment,
        })
        if t.status == 'Completed':
            task_counts['completed'] += 1
        elif overdue:
            task_counts['overdue'] += 1
        elif t.status in ('Pending Approval', 'Needs Revision'):
            task_counts['needs_attention'] += 1
        else:
            task_counts['open'] += 1

    existing_titles = {r.title.strip().lower() for r in all_risks}
    catalog = [dict(item, in_register=item['title'].strip().lower() in existing_titles) for item in RISK_CATALOG]

    return render_template('risks.html', page='risks', risks=risk_dicts,
        tasks=tasks, task_counts=task_counts, task_statuses=TASK_STATUSES, catalog=catalog)


@risks_bp.route('/risks/add', methods=['POST'])
@login_required
@require_permission('write')
def add_risk():
    title = request.form.get('title', '').strip()
    likelihood = request.form.get('likelihood', 'Medium')
    impact = request.form.get('impact', 'Medium')

    if not title:
        flash('Risk title is required.', 'error')
        return redirect(url_for('risks.risks'))

    if likelihood not in RISK_LEVEL_SCORES or impact not in RISK_LEVEL_SCORES:
        flash('Invalid likelihood or impact level.', 'error')
        return redirect(url_for('risks.risks'))

    risk = Risk(
        title=title,
        description=request.form.get('description', ''),
        category=request.form.get('category', ''),
        likelihood=likelihood,
        impact=impact,
        score=RISK_LEVEL_SCORES[likelihood] * RISK_LEVEL_SCORES[impact],
        owner=request.form.get('owner', ''),
        status='Open',
        treatment=request.form.get('treatment', 'Mitigate'),
        created=datetime.utcnow().strftime('%Y-%m-%d'),
    )
    db.session.add(risk)
    log_activity('created', 'Risk', title)
    db.session.commit()
    notify_risk_escalated(risk)

    flash(f'Risk "{title}" added.', 'success')
    return redirect(url_for('risks.risks'))


@risks_bp.route('/risks/<int:risk_id>/edit', methods=['POST'])
@login_required
@require_permission('write')
def edit_risk(risk_id):
    risk = Risk.query.get_or_404(risk_id)
    title = request.form.get('title', '').strip()
    likelihood = request.form.get('likelihood', risk.likelihood)
    impact = request.form.get('impact', risk.impact)

    if not title:
        flash('Risk title is required.', 'error')
        return redirect(url_for('risks.risks'))

    if likelihood not in RISK_LEVEL_SCORES or impact not in RISK_LEVEL_SCORES:
        flash('Invalid likelihood or impact level.', 'error')
        return redirect(url_for('risks.risks'))

    risk.title = title
    risk.description = request.form.get('description', risk.description)
    risk.category = request.form.get('category', risk.category)
    risk.likelihood = likelihood
    risk.impact = impact
    risk.score = RISK_LEVEL_SCORES[likelihood] * RISK_LEVEL_SCORES[impact]
    risk.owner = request.form.get('owner', risk.owner)
    risk.status = request.form.get('status', risk.status)
    risk.treatment = request.form.get('treatment', risk.treatment)

    log_activity('updated', 'Risk', title)
    db.session.commit()
    notify_risk_escalated(risk)
    flash(f'Risk "{title}" updated.', 'success')
    return redirect(url_for('risks.risks'))


@risks_bp.route('/risks/<int:risk_id>/delete', methods=['POST'])
@login_required
@require_permission('delete')
def delete_risk(risk_id):
    risk = Risk.query.get_or_404(risk_id)
    title = risk.title
    db.session.delete(risk)
    log_activity('deleted', 'Risk', title)
    db.session.commit()
    flash(f'Risk "{title}" deleted.', 'info')
    return redirect(url_for('risks.risks'))


@risks_bp.route('/risks/<int:risk_id>')
@login_required
def risk_detail(risk_id):
    risk = Risk.query.get_or_404(risk_id)
    all_controls = Control.query.order_by(Control.code).all()
    treatments = risk.treatments.order_by(RiskTreatment.created_at.desc()).all()
    return render_template('risk_detail.html', page='risks', risk=risk,
        all_controls=all_controls, treatments=treatments,
        risk_levels=list(RISK_LEVEL_SCORES.keys()))


@risks_bp.route('/risks/<int:risk_id>/controls', methods=['POST'])
@login_required
@require_permission('write')
def update_risk_controls(risk_id):
    risk = Risk.query.get_or_404(risk_id)
    control_ids = request.form.getlist('control_ids')
    risk.mitigating_controls = [Control.query.get(int(cid)) for cid in control_ids if Control.query.get(int(cid))]

    log_activity('updated', 'Risk', risk.title, f'{current_user.name} updated mitigating controls for risk "{risk.title}"')
    db.session.commit()
    flash('Mitigating controls updated.', 'success')
    return redirect(url_for('risks.risk_detail', risk_id=risk_id))


@risks_bp.route('/risks/<int:risk_id>/treatments/add', methods=['POST'])
@login_required
@require_permission('write')
def add_treatment(risk_id):
    risk = Risk.query.get_or_404(risk_id)
    action = request.form.get('action', '').strip()
    if not action:
        flash('Treatment action is required.', 'error')
        return redirect(url_for('risks.risk_detail', risk_id=risk_id))

    treatment = RiskTreatment(
        risk_id=risk.id, action=action,
        owner=request.form.get('owner', ''),
        deadline=request.form.get('deadline', ''),
        status='Planned',
    )
    db.session.add(treatment)
    log_activity('created', 'Risk', risk.title, f'{current_user.name} added a treatment plan to risk "{risk.title}"')
    db.session.commit()
    flash('Treatment plan added.', 'success')
    return redirect(url_for('risks.risk_detail', risk_id=risk_id))


@risks_bp.route('/risks/tasks/add', methods=['POST'])
@login_required
@require_permission('write')
def add_mitigation_task():
    risk = Risk.query.get_or_404(request.form.get('risk_id', type=int))
    action = request.form.get('action', '').strip()
    if not action:
        flash('Task name is required.', 'error')
        return redirect(url_for('risks.risks') + '#tasks')

    db.session.add(RiskTreatment(
        risk_id=risk.id, action=action,
        owner=request.form.get('owner', ''),
        department=request.form.get('department', ''),
        deadline=request.form.get('deadline', ''),
        status='Planned',
    ))
    log_activity('created', 'Risk', risk.title, f'{current_user.name} added a mitigation task to risk "{risk.title}"')
    db.session.commit()
    flash('Mitigation task added.', 'success')
    return redirect(url_for('risks.risks') + '#tasks')


@risks_bp.route('/risks/<int:risk_id>/treatments/<int:treatment_id>/status', methods=['POST'])
@login_required
@require_permission('write')
def update_treatment_status(risk_id, treatment_id):
    treatment = RiskTreatment.query.filter_by(id=treatment_id, risk_id=risk_id).first_or_404()
    risk = treatment.risk
    status = request.form.get('status', treatment.status)
    treatment.status = status

    if status == 'Completed':
        treatment.completed_at = datetime.utcnow()
        residual_likelihood = request.form.get('residual_likelihood')
        residual_impact = request.form.get('residual_impact')
        if residual_likelihood in RISK_LEVEL_SCORES and residual_impact in RISK_LEVEL_SCORES:
            risk.residual_likelihood = residual_likelihood
            risk.residual_impact = residual_impact
            risk.residual_score = RISK_LEVEL_SCORES[residual_likelihood] * RISK_LEVEL_SCORES[residual_impact]

    log_activity('status_changed', 'Risk', risk.title, f'{current_user.name} marked a treatment plan for risk "{risk.title}" as {status}')
    db.session.commit()
    flash(f'Treatment marked as {status}.', 'success')
    if request.form.get('next') == 'tasks':
        return redirect(url_for('risks.risks') + '#tasks')
    return redirect(url_for('risks.risk_detail', risk_id=risk_id))


@risks_bp.route('/risks/discovery/add', methods=['POST'])
@login_required
@require_permission('write')
def add_from_catalog():
    title = request.form.get('title', '').strip()
    if not title:
        return redirect(url_for('risks.risks') + '#discovery')

    if Risk.query.filter(db.func.lower(Risk.title) == title.lower()).first():
        flash(f'"{title}" is already in your risk register.', 'info')
        return redirect(url_for('risks.risks') + '#discovery')

    risk = Risk(
        title=title,
        description=request.form.get('description', ''),
        category=request.form.get('category', ''),
        likelihood='Medium', impact='Medium',
        score=RISK_LEVEL_SCORES['Medium'] * RISK_LEVEL_SCORES['Medium'],
        owner=current_user.name,
        status='Open',
        treatment='Mitigate',
        created=datetime.utcnow().strftime('%Y-%m-%d'),
    )
    db.session.add(risk)
    log_activity('created', 'Risk', title, f'{current_user.name} added "{title}" from the risk discovery library')
    db.session.commit()
    notify_risk_escalated(risk)

    flash(f'"{title}" added to your risk register.', 'success')
    return redirect(url_for('risks.risks') + '#discovery')


@risks_bp.route('/risks/<int:risk_id>/treatments/<int:treatment_id>/milestones/add', methods=['POST'])
@login_required
@require_permission('write')
def add_milestone(risk_id, treatment_id):
    treatment = RiskTreatment.query.filter_by(id=treatment_id, risk_id=risk_id).first_or_404()
    title = request.form.get('title', '').strip()
    if not title:
        flash('Milestone title is required.', 'error')
        return redirect(url_for('risks.risk_detail', risk_id=risk_id))

    db.session.add(TreatmentMilestone(treatment_id=treatment.id, title=title, due_date=request.form.get('due_date', '')))
    log_activity('created', 'Risk', treatment.risk.title, f'{current_user.name} added milestone "{title}" to a treatment plan for risk "{treatment.risk.title}"')
    db.session.commit()
    flash('Milestone added.', 'success')
    return redirect(url_for('risks.risk_detail', risk_id=risk_id))


@risks_bp.route('/risks/<int:risk_id>/milestones/<int:milestone_id>/toggle', methods=['POST'])
@login_required
@require_permission('write')
def toggle_milestone(risk_id, milestone_id):
    milestone = TreatmentMilestone.query.get_or_404(milestone_id)
    milestone.completed = not milestone.completed
    log_activity('status_changed', 'Risk', milestone.treatment.risk.title,
        f'{current_user.name} marked milestone "{milestone.title}" as {"completed" if milestone.completed else "incomplete"}')
    db.session.commit()
    return redirect(url_for('risks.risk_detail', risk_id=risk_id))


@risks_bp.route('/risks/export')
@login_required
def export_risks():
    rows = [(r.title, r.category, r.likelihood, r.impact, r.score, r.owner, r.status, r.treatment, r.created) for r in Risk.query.all()]
    return csv_response('risks.csv', ['Title', 'Category', 'Likelihood', 'Impact', 'Score', 'Owner', 'Status', 'Treatment', 'Created'], rows)


@risks_bp.route('/api/risks/matrix')
@login_required
def api_risk_matrix():
    matrix = {
        "Critical": {"High": 0, "Medium": 0, "Low": 0},
        "High": {"High": 0, "Medium": 0, "Low": 0},
        "Medium": {"High": 0, "Medium": 0, "Low": 0},
        "Low": {"High": 0, "Medium": 0, "Low": 0},
    }
    for r in Risk.query.all():
        if r.impact in matrix and r.likelihood in matrix[r.impact]:
            matrix[r.impact][r.likelihood] += 1
    return jsonify(matrix)
