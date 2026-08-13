from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Policy, PolicyAcknowledgement, Employee

policies_bp = Blueprint('policies', __name__)


@policies_bp.route('/policies')
@login_required
def policies():
    all_policies = Policy.query.all()
    all_employees = Employee.query.order_by(Employee.name).all()

    unacked_by_policy = {}
    for policy in all_policies:
        acked_ids = {a.employee_id for a in policy.acks}
        unacked_by_policy[policy.id] = [
            {'id': e.id, 'name': e.name} for e in all_employees if e.id not in acked_ids
        ]

    return render_template('policies.html', page='policies', policies=all_policies,
        policy_dicts=[p.to_dict() for p in all_policies],
        unacked_by_policy=unacked_by_policy)


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
        status=request.form.get('status', 'Draft'),
        framework=request.form.get('framework', ''),
        review_cycle_days=review_cycle_days,
        last_reviewed=today.strftime('%Y-%m-%d'),
        next_review=(today + timedelta(days=review_cycle_days)).strftime('%Y-%m-%d'),
    )
    db.session.add(policy)
    db.session.commit()

    flash(f'Policy "{name}" {"published" if policy.status == "Published" else "saved as draft"}.', 'success')
    return redirect(url_for('policies.policies'))


@policies_bp.route('/policies/<int:policy_id>/edit', methods=['POST'])
@login_required
def edit_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    name = request.form.get('name', '').strip()
    if not name:
        flash('Policy name is required.', 'error')
        return redirect(url_for('policies.policies'))

    try:
        next_version = round(float(policy.version) + 0.1, 1)
    except (TypeError, ValueError):
        next_version = 1.1

    policy.name = name
    policy.content = request.form.get('content', policy.content)
    policy.owner = request.form.get('owner', policy.owner)
    policy.framework = request.form.get('framework', policy.framework)
    policy.status = request.form.get('status', policy.status)
    policy.version = str(next_version)
    policy.last_reviewed = datetime.utcnow().strftime('%Y-%m-%d')
    review_cycle_days = int(request.form.get('review_cycle_days') or policy.review_cycle_days)
    policy.review_cycle_days = review_cycle_days
    policy.next_review = (datetime.utcnow().date() + timedelta(days=review_cycle_days)).strftime('%Y-%m-%d')

    db.session.commit()
    flash(f'Policy "{name}" updated to v{policy.version}.', 'success')
    return redirect(url_for('policies.policies'))


@policies_bp.route('/policies/<int:policy_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    employee_ids = request.form.getlist('employee_ids')

    already_acked = {a.employee_id for a in policy.acks}
    added = 0
    for employee_id in employee_ids:
        employee_id = int(employee_id)
        if employee_id not in already_acked:
            db.session.add(PolicyAcknowledgement(policy_id=policy.id, employee_id=employee_id))
            added += 1

    db.session.commit()
    flash(f'{added} employee(s) recorded as acknowledging "{policy.name}".', 'success')
    return redirect(url_for('policies.policies'))


@policies_bp.route('/policies/<int:policy_id>/delete', methods=['POST'])
@login_required
def delete_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    name = policy.name
    db.session.delete(policy)
    db.session.commit()
    flash(f'Policy "{name}" deleted.', 'info')
    return redirect(url_for('policies.policies'))
