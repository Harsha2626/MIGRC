from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import (
    db, Employee, TrainingCampaign, TrainingCampaignEnrollment,
    EmployeeAccess, AccessReview, Vendor,
)
from app.services.activity import log_activity
from app.utils import require_permission

people_bp = Blueprint('people', __name__)


VENDOR_ICONS = {
    'aws': 'fa-aws',
    'amazon': 'fa-aws',
    'google': 'fa-google',
    'github': 'fa-github',
    'slack': 'fa-slack',
    'microsoft': 'fa-microsoft',
    'azure': 'fa-microsoft',
}


@people_bp.app_template_filter('vendor_icon')
def vendor_icon(name):
    if not name:
        return 'fa-plug'
    lowered = name.lower()
    for key, icon in VENDOR_ICONS.items():
        if key in lowered:
            return icon
    return 'fa-plug'


# ============================================================
# EMPLOYEES
# ============================================================

@people_bp.route('/people/employees')
@login_required
def employees():
    tab = request.args.get('tab', 'overview')
    department = request.args.get('department', '')
    task_status = request.args.get('task_status', '')
    group_id = request.args.get('group', '')
    search = request.args.get('q', '')

    all_employees = Employee.query.order_by(Employee.name).all()
    campaigns = TrainingCampaign.query.order_by(TrainingCampaign.name).all()

    # ---- Overview tab ----
    overview_employees = all_employees
    if group_id:
        campaign = TrainingCampaign.query.get(int(group_id))
        if campaign:
            enrolled_ids = {e.employee_id for e in campaign.enrollments}
            overview_employees = [e for e in all_employees if e.id in enrolled_ids]

    total_overview = len(overview_employees)
    pending_tasks_count = len([e for e in overview_employees if e.has_pending_tasks])
    monitoring_count = len([e for e in overview_employees if e.monitoring_agent_installed])
    device_compliant_count = len([e for e in overview_employees if e.device_security_compliant])
    policy_accepted_count = len([e for e in overview_employees if e.policy_acknowledged])
    policy_not_accepted_count = total_overview - policy_accepted_count

    total_enrollments = sum(e.enrollments.count() for e in overview_employees)
    completed_enrollments = sum(e.enrollments.filter_by(completed=True).count() for e in overview_employees)
    incomplete_enrollments = total_enrollments - completed_enrollments

    # ---- All Employees tab ----
    filtered = all_employees
    if department:
        filtered = [e for e in filtered if e.department == department]
    if task_status == 'pending':
        filtered = [e for e in filtered if e.has_pending_tasks]
    elif task_status == 'clear':
        filtered = [e for e in filtered if not e.has_pending_tasks]
    if group_id:
        campaign = TrainingCampaign.query.get(int(group_id))
        if campaign:
            enrolled_ids = {e.employee_id for e in campaign.enrollments}
            filtered = [e for e in filtered if e.id in enrolled_ids]
    if search:
        s = search.lower()
        filtered = [e for e in filtered if s in e.name.lower() or s in e.email.lower()]

    departments = sorted({e.department for e in all_employees if e.department})

    return render_template('people_employees.html',
        page='employees',
        tab=tab,
        employees=filtered,
        all_employees_count=len(all_employees),
        active_count=len([e for e in all_employees if e.status == 'Active']),
        offboarding_count=len([e for e in all_employees if e.status == 'Offboarding Needed']),
        offboarded_count=len([e for e in all_employees if e.status == 'Offboarded']),
        non_personnel_count=len([e for e in all_employees if e.status == 'Non Personnel']),
        campaigns=campaigns,
        campaigns_json=[{'id': c.id, 'name': c.name} for c in campaigns],
        departments=departments,
        selected_department=department,
        selected_task_status=task_status,
        selected_group=group_id,
        search=search,
        total_overview=total_overview,
        pending_tasks_count=pending_tasks_count,
        monitoring_count=monitoring_count,
        device_compliant_count=device_compliant_count,
        policy_accepted_count=policy_accepted_count,
        policy_not_accepted_count=policy_not_accepted_count,
        completed_enrollments=completed_enrollments,
        incomplete_enrollments=incomplete_enrollments,
    )


@people_bp.route('/people/employees', methods=['POST'])
@login_required
@require_permission('write')
def create_employee():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    department = request.form.get('department', '').strip()
    source = request.form.get('source', 'Manual')
    status = request.form.get('status', 'Active')
    campaign_ids = request.form.getlist('campaign_ids')

    if not name or not email:
        flash('Name and email are required.', 'error')
        return redirect(url_for('people.employees', tab='all'))

    if Employee.query.filter_by(email=email).first():
        flash('An employee with that email already exists.', 'error')
        return redirect(url_for('people.employees', tab='all'))

    employee = Employee(name=name, email=email, department=department, source=source, status=status)
    db.session.add(employee)
    db.session.flush()

    for cid in campaign_ids:
        db.session.add(TrainingCampaignEnrollment(campaign_id=int(cid), employee_id=employee.id))

    log_activity('created', 'Employee', name)
    db.session.commit()

    flash(f'Employee {name} added successfully.', 'success')
    return redirect(url_for('people.employees', tab='all'))


@people_bp.route('/people/employees/<int:employee_id>/edit', methods=['POST'])
@login_required
@require_permission('write')
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    status = request.form.get('status', employee.status)
    department = request.form.get('department', employee.department)
    campaign_ids = {int(cid) for cid in request.form.getlist('campaign_ids')}

    employee.status = status
    employee.department = department
    if status == 'Offboarded' and not employee.offboarded_at:
        employee.offboarded_at = datetime.utcnow()
    elif status != 'Offboarded':
        employee.offboarded_at = None

    current_ids = {e.campaign_id for e in employee.enrollments}
    for cid in campaign_ids - current_ids:
        db.session.add(TrainingCampaignEnrollment(campaign_id=cid, employee_id=employee.id))
    for enrollment in employee.enrollments.filter(TrainingCampaignEnrollment.campaign_id.in_(current_ids - campaign_ids)):
        db.session.delete(enrollment)

    log_activity('updated', 'Employee', employee.name)
    db.session.commit()
    flash(f'{employee.name} updated.', 'success')
    return redirect(url_for('people.employees', tab='all'))


@people_bp.route('/people/employees/<int:employee_id>/delete', methods=['POST'])
@login_required
@require_permission('delete')
def delete_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    name = employee.name
    db.session.delete(employee)
    log_activity('deleted', 'Employee', name)
    db.session.commit()
    flash(f'{name} removed.', 'info')
    return redirect(url_for('people.employees', tab='all'))


# ============================================================
# TRAINING CAMPAIGNS
# ============================================================

@people_bp.route('/people/training-campaigns')
@login_required
def training_campaigns():
    campaigns = TrainingCampaign.query.order_by(TrainingCampaign.created_at.desc()).all()
    drafts = [c for c in campaigns if c.status == 'Draft']
    upcoming = [c for c in campaigns if c.status == 'Upcoming']
    in_progress = [c for c in campaigns if c.status == 'In Progress']
    completed = [c for c in campaigns if c.status == 'Completed']

    return render_template('training.html',
        page='training_campaigns',
        campaigns=campaigns,
        created_count=len(drafts) + len(upcoming),
        draft_count=len(drafts),
        upcoming_count=len(upcoming),
        in_progress_count=len(in_progress),
        completed_count=len(completed),
        employee_count=Employee.query.count(),
    )


@people_bp.route('/people/training-campaigns', methods=['POST'])
@login_required
@require_permission('write')
def create_training_campaign():
    name = request.form.get('name', '').strip()
    status = request.form.get('status', 'Draft')
    launch_date = request.form.get('launch_date', '')
    end_date = request.form.get('end_date', '')
    assign_to = request.form.get('assign_to', 'none')

    if not name:
        flash('Campaign name is required.', 'error')
        return redirect(url_for('people.training_campaigns'))

    campaign = TrainingCampaign(name=name, status=status, launch_date=launch_date, end_date=end_date)
    db.session.add(campaign)
    db.session.flush()

    if assign_to == 'all':
        for employee in Employee.query.all():
            db.session.add(TrainingCampaignEnrollment(campaign_id=campaign.id, employee_id=employee.id))

    log_activity('created', 'TrainingCampaign', name)
    db.session.commit()
    flash(f'Campaign "{name}" created.', 'success')
    return redirect(url_for('people.training_campaigns'))


@people_bp.route('/people/training-campaigns/<int:campaign_id>/delete', methods=['POST'])
@login_required
@require_permission('delete')
def delete_training_campaign(campaign_id):
    campaign = TrainingCampaign.query.get_or_404(campaign_id)
    name = campaign.name
    db.session.delete(campaign)
    log_activity('deleted', 'TrainingCampaign', name)
    db.session.commit()
    flash(f'Campaign "{name}" deleted.', 'info')
    return redirect(url_for('people.training_campaigns'))


# ============================================================
# ACCESS REVIEWS
# ============================================================

@people_bp.route('/people/access-reviews')
@login_required
def access_reviews():
    tab = request.args.get('tab', 'reviews')
    reviews = AccessReview.query.order_by(AccessReview.created_at.desc()).all()
    vendors = Vendor.query.order_by(Vendor.name).all()

    access_by_vendor = {}
    for vendor in vendors:
        access_by_vendor[vendor.id] = EmployeeAccess.query.filter_by(vendor_id=vendor.id).count()

    linked_reviews_by_vendor = {v.id: len(v.access_reviews) for v in vendors}

    chart_labels = [v.name for v in vendors]
    chart_data = [access_by_vendor.get(v.id, 0) for v in vendors]

    return render_template('access_reviews.html',
        page='access_reviews',
        tab=tab,
        reviews=reviews,
        vendors=vendors,
        access_by_vendor=access_by_vendor,
        linked_reviews_by_vendor=linked_reviews_by_vendor,
        chart_labels=chart_labels,
        chart_data=chart_data,
        created_count=len([r for r in reviews if r.status == 'Created']),
        in_progress_count=len([r for r in reviews if r.status == 'In Progress']),
        overdue_count=len([r for r in reviews if r.status == 'Overdue']),
        archived_count=len([r for r in reviews if r.status == 'Archived']),
        completed_count=len([r for r in reviews if r.status == 'Completed']),
    )


@people_bp.route('/people/access-reviews', methods=['POST'])
@login_required
@require_permission('write')
def create_access_review():
    name = request.form.get('name', '').strip()
    owner = request.form.get('owner', '').strip()
    review_period_start = request.form.get('review_period_start', '')
    review_period_end = request.form.get('review_period_end', '')
    recurrence = request.form.get('recurrence', 'Once')
    status = request.form.get('status', 'Created')
    vendor_ids = request.form.getlist('vendor_ids')

    if not name:
        flash('Review name is required.', 'error')
        return redirect(url_for('people.access_reviews'))

    review = AccessReview(
        name=name, owner=owner, status=status,
        review_period_start=review_period_start, review_period_end=review_period_end,
        recurrence=recurrence,
    )
    if vendor_ids:
        review.applications = Vendor.query.filter(Vendor.id.in_(vendor_ids)).all()

    db.session.add(review)
    log_activity('created', 'AccessReview', name)
    db.session.commit()

    flash(f'Access review "{name}" created.', 'success')
    return redirect(url_for('people.access_reviews'))


@people_bp.route('/people/access-reviews/<int:review_id>/status', methods=['POST'])
@login_required
@require_permission('write')
def update_access_review_status(review_id):
    review = AccessReview.query.get_or_404(review_id)
    review.status = request.form.get('status', review.status)
    log_activity('status_changed', 'AccessReview', review.name,
        f'{current_user.name} marked access review "{review.name}" as {review.status}')
    db.session.commit()
    flash(f'"{review.name}" marked as {review.status}.', 'success')
    return redirect(url_for('people.access_reviews'))


@people_bp.route('/people/access-reviews/<int:review_id>/delete', methods=['POST'])
@login_required
@require_permission('delete')
def delete_access_review(review_id):
    review = AccessReview.query.get_or_404(review_id)
    name = review.name
    db.session.delete(review)
    log_activity('deleted', 'AccessReview', name)
    db.session.commit()
    flash(f'Access review "{name}" deleted.', 'info')
    return redirect(url_for('people.access_reviews'))


# ============================================================
# LEGACY REDIRECTS
# ============================================================

@people_bp.route('/training')
@login_required
def training_redirect():
    return redirect(url_for('people.training_campaigns'))


@people_bp.route('/access-reviews')
@login_required
def access_reviews_redirect():
    return redirect(url_for('people.access_reviews'))
