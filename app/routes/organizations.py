import re
from flask import Blueprint, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app.models import db, Organization, OrganizationMembership

organizations_bp = Blueprint('organizations', __name__)


def _slugify(name):
    base = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or 'org'
    slug = base
    suffix = 2
    while Organization.query.filter_by(slug=slug).first():
        slug = f'{base}-{suffix}'
        suffix += 1
    return slug


@organizations_bp.route('/organizations/switch/<int:org_id>', methods=['POST'])
@login_required
def switch_organization(org_id):
    membership = OrganizationMembership.query.filter_by(
        user_id=current_user.id, organization_id=org_id).first()
    if not membership:
        flash("You don't have access to that organization.", 'error')
        return redirect(request.referrer or url_for('main.dashboard'))

    session['current_org_id'] = org_id
    flash(f'Switched to {membership.organization.name}.', 'success')
    # Always land on the dashboard rather than the referring page: the page the user was
    # on may reference a record (e.g. /compliance/<id>) that belongs to the org they just
    # switched away from, which would now 404.
    return redirect(url_for('main.dashboard'))


@organizations_bp.route('/organizations/create', methods=['POST'])
@login_required
def create_organization():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Organization name is required.', 'error')
        return redirect(request.referrer or url_for('main.dashboard'))

    org = Organization(name=name, slug=_slugify(name))
    db.session.add(org)
    db.session.flush()
    db.session.add(OrganizationMembership(user_id=current_user.id, organization_id=org.id, role='Admin'))
    db.session.commit()

    session['current_org_id'] = org.id
    flash(f'Organization "{name}" created — you are its Admin. Let\'s get it set up.', 'success')
    return redirect(url_for('setup.setup_wizard'))
