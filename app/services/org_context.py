from flask import session
from flask_login import current_user
from app.models import OrganizationMembership


def get_current_org():
    """Returns (Organization, OrganizationMembership) for the logged-in user's active org.

    Defaults to the user's first membership and repairs an invalid/stale session value
    (e.g. they were removed from the org they last had selected).
    """
    org_id = session.get('current_org_id')
    if org_id:
        membership = OrganizationMembership.query.filter_by(
            user_id=current_user.id, organization_id=org_id).first()
        if membership:
            return membership.organization, membership

    membership = OrganizationMembership.query.filter_by(
        user_id=current_user.id).order_by(OrganizationMembership.id).first()
    if membership:
        session['current_org_id'] = membership.organization_id
        return membership.organization, membership

    return None, None
