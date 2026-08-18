import difflib
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Policy, PolicyAcknowledgement, PolicyVersion, PolicyReview, Employee, User
from app.services.activity import log_activity
from app.utils import parse_date_safe

policies_bp = Blueprint('policies', __name__)


@policies_bp.route('/policies')
@login_required
def policies():
    all_policies = Policy.query.all()
    all_employees = Employee.query.order_by(Employee.name).all()

    unacked_by_policy = {}
    review_due_soon = {}
    today = date.today()
    for policy in all_policies:
        acked_ids = {a.employee_id for a in policy.acks}
        unacked_by_policy[policy.id] = [
            {'id': e.id, 'name': e.name} for e in all_employees if e.id not in acked_ids
        ]
        due_date = parse_date_safe(policy.next_review)
        review_due_soon[policy.id] = bool(due_date and (due_date - today).days <= 30)

    return render_template('policies.html', page='policies', policies=all_policies,
        policy_dicts=[p.to_dict() for p in all_policies],
        unacked_by_policy=unacked_by_policy,
        review_due_soon=review_due_soon)


@policies_bp.route('/policies/add', methods=['POST'])
@login_required
def add_policy():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Policy name is required.', 'error')
        return redirect(url_for('policies.policies'))

    review_cycle_days = int(request.form.get('review_cycle_days') or 180)
    today = datetime.utcnow().date()

    policy = Policy(
        name=name,
        content=request.form.get('content', ''),
        version='1.0',
        owner=request.form.get('owner', ''),
        status='Draft',
        framework=request.form.get('framework', ''),
        review_cycle_days=review_cycle_days,
        last_reviewed=today.strftime('%Y-%m-%d'),
        next_review=(today + timedelta(days=review_cycle_days)).strftime('%Y-%m-%d'),
    )
    db.session.add(policy)
    log_activity('created', 'Policy', name)
    db.session.commit()

    flash(f'Policy "{name}" created as Draft.', 'success')
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

    return render_template('policy_detail.html', page='policies',
        policy=policy, users=users, versions=versions, reviews=reviews,
        unacked=unacked, acked=acked)


@policies_bp.route('/policies/<int:policy_id>/edit', methods=['POST'])
@login_required
def edit_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    name = request.form.get('name', '').strip()
    if not name:
        flash('Policy name is required.', 'error')
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

    policy.name = name
    policy.content = new_content
    policy.owner = request.form.get('owner', policy.owner)
    policy.framework = request.form.get('framework', policy.framework)
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
def submit_for_review(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    if policy.status != 'Draft':
        flash('Only Draft policies can be submitted for review.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    reviewer_id = request.form.get('reviewer_id')
    if not reviewer_id:
        flash('Please assign a reviewer.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    policy.assigned_reviewer_id = int(reviewer_id)
    policy.status = 'In Review'
    reviewer = User.query.get(int(reviewer_id))

    log_activity('status_changed', 'Policy', policy.name,
        f'{current_user.name} submitted policy "{policy.name}" for review by {reviewer.name if reviewer else "someone"}')
    db.session.commit()
    flash(f'Submitted for review by {reviewer.name if reviewer else "the assigned reviewer"}.', 'success')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


@policies_bp.route('/policies/<int:policy_id>/review', methods=['POST'])
@login_required
def review_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    if policy.status != 'In Review':
        flash('This policy is not awaiting review.', 'error')
        return redirect(url_for('policies.policy_detail', policy_id=policy_id))

    decision = request.form.get('decision')
    comments = request.form.get('comments', '')

    db.session.add(PolicyReview(
        policy_id=policy.id, reviewer_id=current_user.id,
        status='Approved' if decision == 'approve' else 'Rejected',
        comments=comments,
    ))
    policy.status = 'Approved' if decision == 'approve' else 'Draft'

    log_activity('approved' if decision == 'approve' else 'rejected', 'Policy', policy.name,
        f'{current_user.name} {"approved" if decision == "approve" else "sent back"} policy "{policy.name}"')
    db.session.commit()
    flash(f'Policy {"approved" if decision == "approve" else "sent back to Draft"}.', 'success')
    return redirect(url_for('policies.policy_detail', policy_id=policy_id))


@policies_bp.route('/policies/<int:policy_id>/status', methods=['POST'])
@login_required
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


@policies_bp.route('/policies/<int:policy_id>/delete', methods=['POST'])
@login_required
def delete_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    name = policy.name
    db.session.delete(policy)
    log_activity('deleted', 'Policy', name)
    db.session.commit()
    flash(f'Policy "{name}" deleted.', 'info')
    return redirect(url_for('policies.policies'))
