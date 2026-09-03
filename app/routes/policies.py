import os
import difflib
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import (
    db, Policy, PolicyAcknowledgement, PolicyVersion, PolicyReview, PolicyComment, PolicyApproval,
    Employee, User, Control, Framework, ActivityLog,
)
from app.services.activity import log_activity
from app.services.csv_export import csv_response
from app.utils import parse_date_safe, require_permission, allowed_file

policies_bp = Blueprint('policies', __name__)

POLICY_DEPARTMENTS = ['Engineering', 'IT', 'Security', 'Legal', 'HR', 'Finance', 'Governance', 'Compliance']
POLICY_EFFORT_LEVELS = ['Low', 'Medium', 'High']
POLICY_RECURRENCES = ['Once', 'Monthly', 'Quarterly', 'Annually']
STATUS_BADGE = {
    'Not Uploaded': 'badge-neutral',
    'Draft': 'badge-neutral',
    'Needs Review': 'badge-warning',
    'Pending Approval': 'badge-info',
    'Approved': 'badge-primary',
    'Published': 'badge-success',
    'Retired': 'badge-neutral',
}


@policies_bp.route('/policies')
@login_required
def policies():
    all_policies = Policy.query.all()
    all_employees = Employee.query.order_by(Employee.name).all()
    all_users = User.query.order_by(User.name).all()
    all_frameworks = Framework.query.order_by(Framework.name).all()

    # Dashboard filters (Assignee / Department / Framework)
    selected_assignee = request.args.get('assignee', '')
    selected_department = request.args.get('department', '')
    selected_framework = request.args.get('framework', '')

    def assignee_label(policy):
        return policy.assignees[0].name if policy.assignees else 'No Assignee'

    dashboard_policies = [
        p for p in all_policies
        if (not selected_assignee or assignee_label(p) == selected_assignee)
        and (not selected_department or p.department == selected_department)
        and (not selected_framework or p.framework == selected_framework)
    ]

    unacked_by_policy = {}
    review_due_soon = {}
    upcoming_reviews = []
    today = date.today()
    for policy in dashboard_policies:
        acked_ids = {a.employee_id for a in policy.acks}
        unacked_by_policy[policy.id] = [
            {'id': e.id, 'name': e.name} for e in all_employees if e.id not in acked_ids
        ]
        due_date = parse_date_safe(policy.next_review)
        due_soon = bool(due_date and 0 <= (due_date - today).days <= 30)
        review_due_soon[policy.id] = due_soon
        if due_soon:
            upcoming_reviews.append(policy)
    upcoming_reviews.sort(key=lambda p: p.next_review or '')

    # Dashboard: status breakdown for the stacked progress bar
    status_counts = {s: 0 for s in Policy.STATUS_FLOW}
    for policy in dashboard_policies:
        if policy.status in status_counts:
            status_counts[policy.status] += 1
    published_count = status_counts.get('Published', 0)
    total_count = len(dashboard_policies)

    # Dashboard: policies-by-assignee stacked bar chart data
    assignee_buckets = {}
    for policy in dashboard_policies:
        label = assignee_label(policy)
        bucket = assignee_buckets.setdefault(label, {s: 0 for s in Policy.STATUS_FLOW})
        bucket[policy.status] = bucket.get(policy.status, 0) + 1
    chart_labels = sorted(assignee_buckets.keys(), key=lambda l: (l == 'No Assignee', l))
    chart_datasets = [
        {
            'label': s,
            'data': [assignee_buckets[label][s] for label in chart_labels],
            'backgroundColor': color,
        }
        for s, color in [
            ('Not Uploaded', '#94a3b8'), ('Draft', '#cbd5e1'), ('Needs Review', '#f59e0b'),
            ('Pending Approval', '#3b82f6'), ('Approved', '#8b5cf6'), ('Published', '#10b981'),
            ('Retired', '#64748b'),
        ]
    ]

    return render_template('policies.html', page='policies', policies=dashboard_policies,
        policy_dicts=[p.to_dict() for p in dashboard_policies],
        unacked_by_policy=unacked_by_policy,
        review_due_soon=review_due_soon,
        upcoming_reviews=upcoming_reviews,
        status_counts=status_counts, published_count=published_count, total_count=total_count,
        chart_labels=chart_labels, chart_datasets=chart_datasets,
        all_users=all_users, all_frameworks=all_frameworks, policies_status_flow=Policy.STATUS_FLOW,
        POLICY_DEPARTMENTS=POLICY_DEPARTMENTS, STATUS_BADGE=STATUS_BADGE,
        selected_assignee=selected_assignee, selected_department=selected_department,
        selected_framework=selected_framework,
        STATUS_COLORS={'Not Uploaded': '#94a3b8', 'Draft': '#cbd5e1', 'Needs Review': '#f59e0b',
            'Pending Approval': '#3b82f6', 'Approved': '#8b5cf6', 'Published': '#10b981', 'Retired': '#64748b'})


@policies_bp.route('/policies/add', methods=['POST'])
@login_required
@require_permission('write')
def add_policy():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Policy name is required.', 'error')
        return redirect(url_for('policies.policies'))

    review_cycle_days = int(request.form.get('review_cycle_days') or 180)
    today = datetime.utcnow().date()

    policy = Policy(
        name=name,
        version='1.0',
        owner=request.form.get('owner', ''),
        status='Not Uploaded',
        framework=request.form.get('framework', ''),
        department=request.form.get('department') or None,
        requirement_text=request.form.get('requirement_text', '').strip() or None,
        review_cycle_days=review_cycle_days,
        last_reviewed=today.strftime('%Y-%m-%d'),
        next_review=(today + timedelta(days=review_cycle_days)).strftime('%Y-%m-%d'),
    )
    db.session.add(policy)
    log_activity('created', 'Policy', name)
    db.session.commit()

    flash(f'Policy "{name}" created. Choose how to start it below.', 'success')
    return redirect(url_for('policies.policy_detail', policy_id=policy.id))


@policies_bp.route('/policies/<int:policy_id>')
@login_required
def policy_detail(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    users = User.query.order_by(User.name).all()
    versions = policy.versions.all()
    reviews = policy.reviews.all()
    unacked = [e for e in Employee.query.order_by(Employee.name).all()
               if e.id not in {a.employee_id for a in policy.acks}]
    acked = [a for a in policy.acks]

    comments = policy.comments.all()
    approvals = policy.approvals.all()
    linked_controls = policy.controls
    linked_control_ids = {c.id for c in linked_controls}
    linkable_controls = [c for c in Control.query.order_by(Control.code).all() if c.id not in linked_control_ids]
    audit_logs = ActivityLog.query.filter_by(entity_type='Policy', entity_name=policy.name).order_by(ActivityLog.created_at.desc()).all()

    return render_template('policy_detail.html', page='policies',
        policy=policy, users=users, versions=versions, reviews=reviews,
        unacked=unacked, acked=acked, comments=comments, approvals=approvals,
        linked_controls=linked_controls, linkable_controls=linkable_controls, audit_logs=audit_logs,
        POLICY_DEPARTMENTS=POLICY_DEPARTMENTS, POLICY_EFFORT_LEVELS=POLICY_EFFORT_LEVELS,
        POLICY_RECURRENCES=POLICY_RECURRENCES, STATUS_BADGE=STATUS_BADGE)


@policies_bp.route('/policies/<int:policy_id>/edit', methods=['POST'])
@login_required
@require_permission('write')
def edit_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    name = request.form.get('name', '').strip()
    if not name:
        flash('Policy name is required.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    content_changed = False
    if 'content' in request.form:
        if policy.content_state != 'content':
            flash('This policy is stored as an uploaded file or an external link and cannot be edited here.', 'error')
            return redirect(url_for('policies.policy_detail', policy_id=policy_id))
        new_content = request.form.get('content', policy.content)
        content_changed = new_content != policy.content
        if content_changed:
            db.session.add(PolicyVersion(
                policy_id=policy.id, version=policy.version,
                content=policy.content, created_by=current_user.name,
            ))
            try:
                next_version = round(float(policy.version) + 0.1, 1)
            except (TypeError, ValueError):
                next_version = 1.1
            policy.version = str(next_version)
        policy.content = new_content

    policy.name = name
    policy.owner = request.form.get('owner', policy.owner)
    policy.framework = request.form.get('framework', policy.framework)
    policy.department = request.form.get('department', policy.department) or None
    policy.recurrence = request.form.get('recurrence', policy.recurrence)
    policy.effort_estimate = request.form.get('effort_estimate', policy.effort_estimate)
    policy.entities = request.form.get('entities', policy.entities)
    if 'requirement_text' in request.form:
        policy.requirement_text = request.form.get('requirement_text', '').strip() or None
    policy.last_reviewed = datetime.utcnow().strftime('%Y-%m-%d')
    review_cycle_days = int(request.form.get('review_cycle_days') or policy.review_cycle_days)
    policy.review_cycle_days = review_cycle_days
    policy.next_review = (datetime.utcnow().date() + timedelta(days=review_cycle_days)).strftime('%Y-%m-%d')

    log_activity('updated', 'Policy', name, f'{current_user.name} updated policy "{name}"' + (f' to v{policy.version}' if content_changed else ''))
    db.session.commit()
    flash(f'Policy "{name}" updated' + (f' to v{policy.version}' if content_changed else '') + '.', 'success')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


@policies_bp.route('/policies/<int:policy_id>/submit-review', methods=['POST'])
@login_required
@require_permission('write')
def submit_for_review(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    if policy.status != 'Draft':
        flash('Only Draft policies can be submitted for review.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    reviewer_id = request.form.get('reviewer_id')
    approver_ids = request.form.getlist('approver_ids')
    if not reviewer_id:
        flash('Please assign a reviewer.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))
    if not approver_ids:
        flash('Please assign at least one approver.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    policy.assigned_reviewer_id = int(reviewer_id)
    policy.approvers = User.query.filter(User.id.in_([int(i) for i in approver_ids])).all()
    policy.status = 'Needs Review'
    reviewer = User.query.get(int(reviewer_id))

    log_activity('status_changed', 'Policy', policy.name,
        f'{current_user.name} submitted policy "{policy.name}" for review by {reviewer.name if reviewer else "someone"}')
    db.session.commit()
    flash(f'Submitted for review by {reviewer.name if reviewer else "the assigned reviewer"}.', 'success')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


@policies_bp.route('/policies/<int:policy_id>/review', methods=['POST'])
@login_required
@require_permission('write')
def review_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    if policy.status != 'Needs Review':
        flash('This policy is not awaiting review.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    decision = request.form.get('decision')
    comments = request.form.get('comments', '')

    db.session.add(PolicyReview(
        policy_id=policy.id, reviewer_id=current_user.id,
        status='Approved' if decision == 'approve' else 'Rejected',
        comments=comments,
    ))

    if decision == 'approve':
        PolicyApproval.query.filter_by(policy_id=policy.id).delete()
        for approver in policy.approvers:
            db.session.add(PolicyApproval(policy_id=policy.id, approver_id=approver.id))
        policy.status = 'Pending Approval'
    else:
        policy.status = 'Draft'

    log_activity('approved' if decision == 'approve' else 'rejected', 'Policy', policy.name,
        f'{current_user.name} {"approved" if decision == "approve" else "sent back"} policy "{policy.name}"')
    db.session.commit()
    flash('Policy moved to Pending Approval.' if decision == 'approve' else 'Policy sent back to Draft.', 'success')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


@policies_bp.route('/policies/<int:policy_id>/status', methods=['POST'])
@login_required
@require_permission('write')
def advance_status(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    target = request.form.get('status')

    if target != policy.next_status or policy.status not in ('Approved', 'Published'):
        flash('Invalid status transition.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    policy.status = target
    log_activity('status_changed', 'Policy', policy.name, f'{current_user.name} moved policy "{policy.name}" to {target}')
    db.session.commit()
    flash(f'Policy moved to {target}.', 'success')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


@policies_bp.route('/policies/<int:policy_id>/diff/<int:version_id>')
@login_required
def policy_diff(policy_id, version_id):
    policy = Policy.query.get_or_404(policy_id)
    old_version = PolicyVersion.query.filter_by(id=version_id, policy_id=policy_id).first_or_404()

    diff = difflib.HtmlDiff(wrapcolumn=80).make_table(
        (old_version.content or '').splitlines(),
        (policy.content or '').splitlines(),
        fromdesc=f'v{old_version.version}', todesc=f'v{policy.version} (current)',
        context=True, numlines=2,
    )
    return render_template('policy_diff.html', policy=policy, old_version=old_version, diff=diff)


@policies_bp.route('/policies/<int:policy_id>/acknowledge', methods=['POST'])
@login_required
@require_permission('write')
def acknowledge_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    if policy.status != 'Published':
        flash('Only Published policies can be acknowledged.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    employee_ids = request.form.getlist('employee_ids')

    already_acked = {a.employee_id for a in policy.acks}
    added = 0
    for employee_id in employee_ids:
        employee_id = int(employee_id)
        if employee_id not in already_acked:
            db.session.add(PolicyAcknowledgement(policy_id=policy.id, employee_id=employee_id))
            added += 1

    if added:
        log_activity('acknowledged', 'Policy', policy.name,
            f'{current_user.name} recorded {added} acknowledgement(s) for policy "{policy.name}"')
    db.session.commit()
    flash(f'{added} employee(s) recorded as acknowledging "{policy.name}".', 'success')
    return redirect(request.referrer or url_for('policies.policy_detail', policy_id=policy_id))


@policies_bp.route('/policies/export')
@login_required
def export_policies():
    rows = [(
        p.name, p.version, p.owner, p.status, p.framework, p.department or '', p.recurrence,
        p.effort_estimate, ', '.join(u.name for u in p.assignees), ', '.join(u.name for u in p.approvers),
        p.last_reviewed, p.next_review, p.acknowledgements, p.total_employees,
        p.created_at.strftime('%Y-%m-%d') if p.created_at else '',
    ) for p in Policy.query.all()]
    return csv_response('policies.csv', [
        'Name', 'Version', 'Owner', 'Status', 'Framework', 'Department', 'Recurrence', 'Effort Estimate',
        'Assignees', 'Approvers', 'Last Reviewed', 'Next Review', 'Acknowledgements', 'Total Employees', 'Added On',
    ], rows)


@policies_bp.route('/policies/<int:policy_id>/delete', methods=['POST'])
@login_required
@require_permission('delete')
def delete_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    name = policy.name
    db.session.delete(policy)
    log_activity('deleted', 'Policy', name)
    db.session.commit()
    flash(f'Policy "{name}" deleted.', 'info')
    return redirect(url_for('policies.policies'))


@policies_bp.route('/policies/bulk-delete', methods=['POST'])
@login_required
@require_permission('delete')
def bulk_delete_policies():
    policy_ids = request.form.getlist('policy_ids')
    count = 0
    for pid in policy_ids:
        p = Policy.query.get(int(pid))
        if p:
            db.session.delete(p)
            count += 1
    if count:
        log_activity('deleted', 'Policy', f'{count} policy(ies)')
        db.session.commit()
        flash(f'{count} policy(ies) deleted.', 'info')
    return redirect(url_for('policies.policies'))


# ---- START-YOUR-POLICY: upload / link / blank (mutually exclusive) ----

@policies_bp.route('/policies/<int:policy_id>/upload', methods=['POST'])
@login_required
@require_permission('write')
def upload_policy_file(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    if policy.content or policy.external_url:
        flash('This policy already has content or a linked URL.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    file = request.files.get('file')
    if not file or file.filename == '':
        flash('Please select a file to upload.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))
    if not allowed_file(file.filename):
        flash('File type not allowed. Use: pdf, png, jpg, csv, xlsx, doc, docx', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file.save(os.path.join(upload_folder, unique_filename))

    policy.file_path = unique_filename
    policy.file_name = filename
    policy.status = 'Draft'
    log_activity('uploaded', 'Policy', policy.name, f'{current_user.name} uploaded a document for policy "{policy.name}"')
    db.session.commit()
    flash('Policy document uploaded.', 'success')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


@policies_bp.route('/policies/<int:policy_id>/link-url', methods=['POST'])
@login_required
@require_permission('write')
def link_policy_url(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    if policy.content or policy.file_path:
        flash('This policy already has content or an uploaded document.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    url = request.form.get('external_url', '').strip()
    if not url:
        flash('Please provide a URL.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    policy.external_url = url
    policy.status = 'Draft'
    log_activity('updated', 'Policy', policy.name, f'{current_user.name} linked an external document for policy "{policy.name}"')
    db.session.commit()
    flash('Policy linked to an external document.', 'success')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


@policies_bp.route('/policies/<int:policy_id>/start-blank', methods=['POST'])
@login_required
@require_permission('write')
def start_blank_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    if policy.file_path or policy.external_url:
        flash('This policy already has an uploaded document or linked URL.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    policy.content = policy.content or ''
    policy.status = 'Draft'
    log_activity('updated', 'Policy', policy.name, f'{current_user.name} started drafting policy "{policy.name}"')
    db.session.commit()
    flash('Ready to draft — start writing below.', 'success')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


@policies_bp.route('/policies/<int:policy_id>/file')
@login_required
def download_policy_file(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    if not policy.file_path:
        abort(404)
    upload_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(upload_folder, policy.file_path, as_attachment=True,
        download_name=policy.file_name or policy.file_path)


# ---- PENDING APPROVAL SIGN-OFF ----

@policies_bp.route('/policies/<int:policy_id>/approvers/sign-off', methods=['POST'])
@login_required
@require_permission('write')
def sign_off_approval(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    if policy.status != 'Pending Approval':
        flash('This policy is not awaiting approval sign-off.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    row = PolicyApproval.query.filter_by(policy_id=policy.id, approver_id=current_user.id, status='Pending').first()
    if not row:
        flash('You are not a pending approver for this policy.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    decision = request.form.get('decision')
    row.status = 'Approved' if decision == 'approve' else 'Rejected'
    row.comments = request.form.get('comments', '')
    row.decided_at = datetime.utcnow()

    if decision == 'approve':
        if all(r.status == 'Approved' for r in policy.approvals):
            policy.status = 'Approved'
        log_activity('approved', 'Policy', policy.name, f'{current_user.name} signed off approval for policy "{policy.name}"')
        flash('Sign-off recorded.', 'success')
    else:
        policy.status = 'Draft'
        log_activity('rejected', 'Policy', policy.name, f'{current_user.name} rejected approval for policy "{policy.name}"')
        flash('Approval rejected — policy sent back to Draft.', 'success')

    db.session.commit()
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


# ---- ASSIGNEES / APPROVERS ROSTER ----

@policies_bp.route('/policies/<int:policy_id>/assignees', methods=['POST'])
@login_required
@require_permission('write')
def update_assignees(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    user_ids = request.form.getlist('user_ids')
    policy.assignees = User.query.filter(User.id.in_([int(i) for i in user_ids])).all() if user_ids else []
    log_activity('updated', 'Policy', policy.name, f'{current_user.name} updated assignees for policy "{policy.name}"')
    db.session.commit()
    flash('Assignees updated.', 'success')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


@policies_bp.route('/policies/<int:policy_id>/approvers', methods=['POST'])
@login_required
@require_permission('write')
def update_approvers(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    if policy.status == 'Pending Approval':
        flash('Cannot change approvers while a sign-off is in progress — reject it back to Draft first.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))
    user_ids = request.form.getlist('user_ids')
    policy.approvers = User.query.filter(User.id.in_([int(i) for i in user_ids])).all() if user_ids else []
    log_activity('updated', 'Policy', policy.name, f'{current_user.name} updated approvers for policy "{policy.name}"')
    db.session.commit()
    flash('Approvers updated.', 'success')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


# ---- COMMENTS ----

@policies_bp.route('/policies/<int:policy_id>/comments/add', methods=['POST'])
@login_required
@require_permission('write')
def add_comment(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    body = request.form.get('body', '').strip()
    if not body:
        flash('Comment cannot be empty.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))
    db.session.add(PolicyComment(policy_id=policy.id, user_id=current_user.id, body=body))
    db.session.commit()
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


@policies_bp.route('/policies/<int:policy_id>/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
@require_permission('delete')
def delete_comment(policy_id, comment_id):
    comment = PolicyComment.query.filter_by(id=comment_id, policy_id=policy_id).first_or_404()
    db.session.delete(comment)
    db.session.commit()
    flash('Comment deleted.', 'info')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


# ---- CONTROLS & REQUIREMENTS LINKING ----

@policies_bp.route('/policies/<int:policy_id>/controls/link', methods=['POST'])
@login_required
@require_permission('write')
def link_controls(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    control_ids = request.form.getlist('control_ids')
    existing_ids = {c.id for c in policy.controls}
    added = 0
    for cid in control_ids:
        cid_int = int(cid)
        if cid_int not in existing_ids:
            control = Control.query.get(cid_int)
            if control:
                policy.controls.append(control)
                added += 1
    if added:
        log_activity('updated', 'Policy', policy.name, f'{current_user.name} linked {added} control(s) to policy "{policy.name}"')
        db.session.commit()
    flash(f'{added} control(s) linked.', 'success')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


@policies_bp.route('/policies/<int:policy_id>/controls/<int:control_id>/unlink', methods=['POST'])
@login_required
@require_permission('write')
def unlink_control(policy_id, control_id):
    policy = Policy.query.get_or_404(policy_id)
    control = Control.query.get_or_404(control_id)
    if control in policy.controls:
        policy.controls.remove(control)
        db.session.commit()
        flash('Control unlinked.', 'info')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))
