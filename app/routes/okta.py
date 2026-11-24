"""Okta integration: employee directory sync via the Okta Users API.

Each org supplies its Okta domain and a read-only API token (SSWS). We validate it with a
GET /api/v1/users?limit=1, store the token Fernet-encrypted, and import users as Employees.
"""
import re
from datetime import datetime
from urllib.parse import urlparse

import requests
from flask import Blueprint, redirect, url_for, flash, request, g, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from app.models import db, OktaConnection, Employee
from app.services.crypto import encrypt, decrypt
from app.utils import require_permission

okta_bp = Blueprint('okta', __name__)

TIMEOUT = 20
# Only genuine Okta hosts: the API token is sent here, so this also blocks SSRF / token exfiltration.
DOMAIN = re.compile(r'^[a-z0-9-]+(\.[a-z0-9-]+)*\.(okta\.com|oktapreview\.com|okta-emea\.com|okta-gov\.com|okta\.mil)$')


def _back():
    return redirect(url_for('integrations.integrations'))


@okta_bp.route('/integrations/okta/connect', methods=['POST'])
@login_required
@require_permission('write')
def connect():
    org = g.current_org
    domain = re.sub(r'^https?://', '', request.form.get('domain', '').strip().lower()).rstrip('/')
    token = request.form.get('api_token', '').strip()
    if not org or not token or not DOMAIN.match(domain):
        flash('Enter your Okta domain (e.g. acme.okta.com) and an API token.', 'error')
        return _back()
    try:
        requests.get(f'https://{domain}/api/v1/users?limit=1', timeout=TIMEOUT, allow_redirects=False,
                     headers={'Authorization': f'SSWS {token}', 'Accept': 'application/json'}).raise_for_status()
    except Exception:
        current_app.logger.exception('Okta credential validation failed')
        flash('Okta rejected that domain or API token (the token needs a read-only admin role).', 'error')
        return _back()

    conn = OktaConnection.query.filter_by(organization_id=org.id).first()
    if not conn:
        conn = OktaConnection(organization_id=org.id)
        db.session.add(conn)
    conn.domain, conn.api_token = domain, encrypt(token)
    conn.connected_by_id = current_user.id
    conn.connected_at = datetime.utcnow()
    db.session.commit()
    flash(f'Connected to Okta ({domain}).', 'success')
    return _back()


@okta_bp.route('/integrations/okta/disconnect', methods=['POST'])
@login_required
@require_permission('write')
def disconnect():
    if g.current_org:
        OktaConnection.query.filter_by(organization_id=g.current_org.id).delete()
        db.session.commit()
    flash('Okta disconnected.', 'info')
    return _back()


@okta_bp.route('/integrations/okta/sync', methods=['POST'])
@login_required
@require_permission('write')
def sync_employees():
    org = g.current_org
    conn = OktaConnection.query.filter_by(organization_id=org.id).first() if org else None
    if not conn:
        flash('Connect Okta first.', 'error')
        return _back()
    users = []
    try:
        token = decrypt(conn.api_token)
        url = f'https://{conn.domain}/api/v1/users?limit=200'
        while url:
            r = requests.get(url, headers={'Authorization': f'SSWS {token}', 'Accept': 'application/json'},
                             timeout=TIMEOUT, allow_redirects=False)
            r.raise_for_status()
            users += r.json()
            url = (r.links.get('next') or {}).get('url')
            if url and urlparse(url).hostname != conn.domain:  # never send the token to another host
                break
    except Exception:
        current_app.logger.exception('Okta directory sync failed')
        flash('Could not read the Okta directory. Check the API token has not expired or been revoked.', 'error')
        return _back()

    created = updated = 0
    for u in users:
        p = u.get('profile') or {}
        email = (p.get('email') or p.get('login') or '').lower()
        if not email:
            continue
        name = (p.get('displayName') or f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() or email)[:100]
        status = 'Active' if u.get('status') == 'ACTIVE' else 'Suspended'
        emp = Employee.query.filter(Employee.organization_id == org.id, func.lower(Employee.email) == email).first()
        if emp:
            # Only flip Active<->Suspended; never resurrect an HR-set Offboarded/Offboarding status.
            if emp.status in ('Active', 'Suspended'):
                emp.status = status
            updated += 1
        else:
            db.session.add(Employee(organization_id=org.id, name=name, email=email, department=(p.get('department') or '')[:50] or None,
                                    source='Okta', status=status))
            created += 1
    conn.last_synced_at = datetime.utcnow()
    db.session.commit()
    flash(f'Synced {created + updated} employee(s) from Okta ({created} new, {updated} updated).', 'success')
    return _back()
