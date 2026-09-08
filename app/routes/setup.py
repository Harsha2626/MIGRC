import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, g, abort
from flask_login import login_required
from werkzeug.utils import secure_filename
from app.models import (
    db, SetupTask, Framework, Policy, Employee, Vendor, Risk, Audit, Evidence,
    Organization, OrganizationMembership, DepartmentOwner,
)
from app.routes.policies import POLICY_DEPARTMENTS
from app.utils import require_permission, allowed_file

setup_bp = Blueprint('setup', __name__)

WORK_ARRANGEMENTS = ['Remote', 'Hybrid', 'Office']
INDUSTRIES = ['Information Technology', 'Healthcare', 'Finance', 'Retail', 'Manufacturing', 'Other']
GEOGRAPHIC_SCOPES = ['India', 'United States', 'United Kingdom', 'European Union', 'Global']

IDENTITY_PROVIDERS = [
    {'name': 'Google Workspace', 'icon': 'fa-brands fa-google'},
    {'name': 'Microsoft Entra (Azure AD)', 'icon': 'fa-brands fa-microsoft'},
    {'name': 'Okta (IDP)', 'icon': 'fa-solid fa-circle-dot'},
    {'name': 'Okta (SSO)', 'icon': 'fa-solid fa-circle-dot'},
    {'name': 'OneLogin', 'icon': 'fa-solid fa-lock'},
    {'name': 'JumpCloud (SSO)', 'icon': 'fa-solid fa-cloud'},
    {'name': 'Auth0', 'icon': 'fa-solid fa-shield-halved'},
    {'name': 'PingOne', 'icon': 'fa-solid fa-p'},
]

CLOUD_PROVIDERS = [
    {'name': 'Amazon Web Services', 'icon': 'fa-brands fa-aws'},
    {'name': 'Microsoft Azure', 'icon': 'fa-brands fa-microsoft'},
    {'name': 'Google Cloud', 'icon': 'fa-brands fa-google'},
]

# Tasks with no natural "did the user do this" signal in the data get a manual
# done/not-done toggle instead of auto-detection.
MANUAL_TASK_KEYS = {'connect_identity_provider', 'connect_cloud_providers'}

SETUP_PHASES = [
    {
        'key': 'prerequisite', 'title': 'Prerequisite Info', 'icon': 'fa-flag',
        'tasks': [
            {'key': 'org_details', 'title': 'Add Your Organization Details',
             'description': 'Begin your journey with MIGRC by sharing a few key details about your organization.'},
            {'key': 'connect_identity_provider', 'title': 'Connect Your Identity Provider',
             'description': 'Integrate with your identity provider (IDP) to sync employee information and track compliance across your workforce.'},
            {'key': 'assign_department_owners', 'title': 'Assign Department Owners',
             'description': 'Select an owner for each department to manage its artifacts.'},
            {'key': 'connect_cloud_providers', 'title': 'Connect Your Cloud Providers',
             'description': 'Integrate with your cloud instances so MIGRC AI can automatically scan for security misconfigurations and vulnerabilities.'},
            {'key': 'schedule_audit', 'title': 'Schedule Internal Audits',
             'description': 'Select tentative internal audit dates for each framework. You can modify these later in the Audit Center.'},
        ],
    },
    {
        'key': 'compliance_setup', 'title': 'Compliance Setup', 'icon': 'fa-file-shield',
        'tasks': [
            {'key': 'choose_frameworks', 'title': 'Choose Your Compliance Frameworks',
             'description': 'Select the frameworks (ISO 27001, SOC 2, etc.) you need to comply with.',
             'link_endpoint': 'compliance.compliance', 'link_label': 'Go to Compliance'},
            {'key': 'add_policies', 'title': 'Add Your Policies',
             'description': 'Create or upload the policies your organization follows.',
             'link_endpoint': 'policies.policies', 'link_label': 'Go to Policies'},
            {'key': 'add_employees', 'title': 'Add Your Employees',
             'description': 'Bring your workforce into MIGRC to track training and access.',
             'link_endpoint': 'people.employees', 'link_label': 'Go to Employees'},
            {'key': 'upload_evidence', 'title': 'Upload Evidence for a Control',
             'description': 'Attach evidence to a control to start tracking compliance.',
             'link_endpoint': 'compliance.compliance', 'link_label': 'Go to Compliance'},
        ],
    },
    {
        'key': 'risk_vendor', 'title': 'Risk & Vendor Management', 'icon': 'fa-triangle-exclamation',
        'tasks': [
            {'key': 'log_risk', 'title': 'Log Your First Risk',
             'description': 'Record a risk in your risk register to start tracking treatment.',
             'link_endpoint': 'risks.risks', 'link_label': 'Go to Risk Management'},
            {'key': 'add_vendors', 'title': 'Add Your Vendors',
             'description': 'Track third-party vendors and their compliance posture.',
             'link_endpoint': 'vendors.vendors', 'link_label': 'Go to Vendors'},
        ],
    },
]


def _auto_completion(org):
    """Tasks backed by real MIGRC data — done the moment the underlying record exists."""
    dept_owners_assigned = False
    if org:
        dept_owners_assigned = DepartmentOwner.query.filter_by(organization_id=org.id) \
            .filter(DepartmentOwner.owner_id.isnot(None)).count() > 0

    return {
        'org_details': bool(org and org.legal_name),
        'assign_department_owners': dept_owners_assigned,
        'choose_frameworks': Framework.query.count() > 0,
        'add_policies': Policy.query.count() > 0,
        'add_employees': Employee.query.count() > 0,
        'upload_evidence': Evidence.query.count() > 0,
        'log_risk': Risk.query.count() > 0,
        'add_vendors': Vendor.query.count() > 0,
        'schedule_audit': Audit.query.count() > 0,
    }


@setup_bp.route('/setup')
@login_required
def setup_wizard():
    org = g.current_org
    auto_done = _auto_completion(org)
    manual_done = {t.task_key: t.completed for t in SetupTask.query.all()}

    org_members = []
    dept_owner_map = {}
    if org:
        org_members = [m.user for m in OrganizationMembership.query.filter_by(organization_id=org.id).all()]
        dept_owner_map = {d.department: d.owner_id for d in DepartmentOwner.query.filter_by(organization_id=org.id).all()}
    departments = sorted(set(POLICY_DEPARTMENTS) | set(dept_owner_map.keys()))

    scheduled_audits = {a.framework: a.start_date for a in Audit.query.all()}

    phases = []
    total_tasks = 0
    total_done = 0
    first_incomplete_key = None
    for phase in SETUP_PHASES:
        tasks = []
        done_count = 0
        for t in phase['tasks']:
            is_manual = t['key'] in MANUAL_TASK_KEYS
            completed = manual_done.get(t['key'], False) if is_manual else auto_done.get(t['key'], False)
            if completed:
                done_count += 1
            elif first_incomplete_key is None:
                first_incomplete_key = t['key']
            task_data = dict(t, completed=completed, manual=is_manual)
            if 'link_endpoint' in t:
                task_data['url'] = url_for(t['link_endpoint'])
            tasks.append(task_data)
        phases.append(dict(phase, tasks=tasks, done=done_count, total=len(tasks)))
        total_tasks += len(tasks)
        total_done += done_count

    return render_template('setup_wizard.html', page='setup', phases=phases,
        total_tasks=total_tasks, total_done=total_done, first_incomplete_key=first_incomplete_key,
        org=org, org_members=org_members, departments=departments, dept_owner_map=dept_owner_map,
        frameworks=Framework.query.order_by(Framework.name).all(), scheduled_audits=scheduled_audits,
        WORK_ARRANGEMENTS=WORK_ARRANGEMENTS, INDUSTRIES=INDUSTRIES, GEOGRAPHIC_SCOPES=GEOGRAPHIC_SCOPES,
        IDENTITY_PROVIDERS=IDENTITY_PROVIDERS, CLOUD_PROVIDERS=CLOUD_PROVIDERS)


@setup_bp.route('/setup/tasks/<task_key>/toggle', methods=['POST'])
@login_required
@require_permission('write')
def toggle_task(task_key):
    if task_key not in MANUAL_TASK_KEYS:
        flash('This task tracks itself automatically based on your data.', 'error')
        return redirect(url_for('setup.setup_wizard'))

    task = SetupTask.query.filter_by(task_key=task_key).first()
    if not task:
        task = SetupTask(task_key=task_key)
        db.session.add(task)

    task.completed = not task.completed
    task.completed_at = datetime.utcnow() if task.completed else None
    db.session.commit()
    return redirect(url_for('setup.setup_wizard'))


@setup_bp.route('/setup/organization/save', methods=['POST'])
@login_required
@require_permission('write')
def save_organization():
    org = g.current_org
    if not org:
        flash('No active organization.', 'error')
        return redirect(url_for('setup.setup_wizard'))

    name = request.form.get('name', '').strip()
    if name:
        org.name = name
    org.legal_name = request.form.get('legal_name', '').strip()
    org.company_url = request.form.get('company_url', '').strip()
    org.work_arrangement = request.form.get('work_arrangement') or org.work_arrangement
    org.business_address = request.form.get('business_address', '').strip()
    org.industry = request.form.get('industry', '').strip()
    org.geographic_scope = request.form.getlist('geographic_scope')

    file = request.files.get('logo')
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        unique_filename = f'org{org.id}_{timestamp}_{filename}'
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename))
        org.logo_path = unique_filename

    db.session.commit()
    flash('Organization details saved.', 'success')
    return redirect(url_for('setup.setup_wizard'))


@setup_bp.route('/setup/organization/<int:org_id>/logo')
@login_required
def organization_logo(org_id):
    org = Organization.query.get_or_404(org_id)
    if not org.logo_path:
        abort(404)
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], org.logo_path)


@setup_bp.route('/setup/department-owners/save', methods=['POST'])
@login_required
@require_permission('write')
def save_department_owners():
    org = g.current_org
    if not org:
        flash('No active organization.', 'error')
        return redirect(url_for('setup.setup_wizard'))

    departments = request.form.getlist('department')
    owner_ids = request.form.getlist('owner_id')

    for department, owner_id in zip(departments, owner_ids):
        department = department.strip()
        if not department:
            continue
        row = DepartmentOwner.query.filter_by(organization_id=org.id, department=department).first()
        if not row:
            row = DepartmentOwner(organization_id=org.id, department=department)
            db.session.add(row)
        row.owner_id = int(owner_id) if owner_id else None

    db.session.commit()
    flash('Department owners saved.', 'success')
    return redirect(url_for('setup.setup_wizard'))


@setup_bp.route('/setup/audits/schedule', methods=['POST'])
@login_required
@require_permission('audit_write')
def schedule_audits():
    framework_ids = request.form.getlist('framework_id')
    dates = request.form.getlist('audit_date')

    for framework_id, audit_date in zip(framework_ids, dates):
        audit_date = audit_date.strip()
        if not audit_date or not framework_id:
            continue
        framework = Framework.query.get(int(framework_id))
        if not framework:
            continue
        existing = Audit.query.filter_by(framework=framework.name).first()
        if existing:
            existing.start_date = audit_date
        else:
            db.session.add(Audit(
                name=f'{framework.name} Audit', framework=framework.name,
                status='Scheduled', start_date=audit_date,
            ))

    db.session.commit()
    flash('Audit schedule saved.', 'success')
    return redirect(url_for('setup.setup_wizard'))
