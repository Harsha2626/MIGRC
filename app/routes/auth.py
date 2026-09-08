from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, g
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, OrganizationMembership
from app.utils import require_permission

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()

            membership = OrganizationMembership.query.filter_by(
                user_id=user.id).order_by(OrganizationMembership.id).first()
            if membership:
                session['current_org_id'] = membership.organization_id

            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))

        flash('Invalid email or password.', 'error')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['POST'])
@login_required
@require_permission('manage_users')
def register():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    role = request.form.get('role', 'Viewer')

    if not email:
        flash('Email is required.', 'error')
        return redirect(url_for('main.settings'))

    if role not in ('Admin', 'Compliance Manager', 'Auditor', 'Viewer'):
        role = 'Viewer'

    org = g.current_org
    if not org:
        flash('No active organization.', 'error')
        return redirect(url_for('main.settings'))

    # Inviting an email that's already a MIGRC user just adds them to this org
    # (this is how one person ends up able to switch between multiple orgs).
    user = User.query.filter_by(email=email).first()
    if user:
        if OrganizationMembership.query.filter_by(user_id=user.id, organization_id=org.id).first():
            flash('That user is already a member of this organization.', 'error')
            return redirect(url_for('main.settings'))
        db.session.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role=role))
        db.session.commit()
        flash(f'{user.name} added to {org.name}.', 'success')
        return redirect(url_for('main.settings'))

    if not name or not password:
        flash('Name and password are required for a new user.', 'error')
        return redirect(url_for('main.settings'))

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role=role))
    db.session.commit()

    flash(f'User {name} created and added to {org.name}.', 'success')
    return redirect(url_for('main.settings'))
