"""Microsoft Entra ID integration: employee-directory sync via Microsoft Graph.

Multi-tenant app registration: each MIGRC organization's admin signs in with their own Entra
tenant (authority 'organizations'), consents to delegated User.Read.All, and we store the
tenant id + encrypted refresh token against that organization. Mirrors google_oauth.py.
"""
import base64
import json
import secrets
from datetime import datetime, timedelta

import requests
from sqlalchemy import func
from flask import Blueprint, redirect, url_for, flash, request, session, g, current_app
from flask_login import login_required, current_user

from app.models import db, EntraConnection, Employee
from app.services.crypto import encrypt, decrypt
from app.utils import require_permission

entra_oauth_bp = Blueprint('entra_oauth', __name__)

AUTHORITY = 'https://login.microsoftonline.com/organizations/oauth2/v2.0'
GRAPH_USERS = ('https://graph.microsoft.com/v1.0/users'
               '?$select=displayName,mail,userPrincipalName,accountEnabled,userType&$top=999')
SCOPES = 'openid profile email offline_access User.Read.All'
TIMEOUT = 20


def _cfg(key):
    return current_app.config.get(key)


def _token_request(data):
    resp = requests.post(f'{AUTHORITY}/token', timeout=TIMEOUT, data={
        'client_id': _cfg('ENTRA_CLIENT_ID'), 'client_secret': _cfg('ENTRA_CLIENT_SECRET'),
        'scope': SCOPES, **data})
    resp.raise_for_status()
    return resp.json()


def _claims(id_token):
    # Safe without signature check: token came straight from Microsoft's token endpoint over TLS
    # (OIDC Core 3.1.3.7). Only used to label the connection; Graph enforces real access.
    payload = id_token.split('.')[1]
    return json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))


def _access_token(conn):
    """Return a valid access token, refreshing (and rotating the refresh token) if expired."""
    if conn.token_expiry and conn.token_expiry > datetime.utcnow() + timedelta(seconds=60):
        return decrypt(conn.access_token)
    tok = _token_request({'grant_type': 'refresh_token', 'refresh_token': decrypt(conn.refresh_token)})
    conn.access_token = encrypt(tok['access_token'])
    if tok.get('refresh_token'):
        conn.refresh_token = encrypt(tok['refresh_token'])
    conn.token_expiry = datetime.utcnow() + timedelta(seconds=int(tok.get('expires_in', 3600)))
    db.session.commit()  # persist the rotated refresh token even if the Graph call below fails
    return tok['access_token']


@entra_oauth_bp.route('/integrations/entra/connect')
@login_required
@require_permission('write')
def connect():
    if not (_cfg('ENTRA_CLIENT_ID') and _cfg('ENTRA_CLIENT_SECRET') and _cfg('ENTRA_REDIRECT_URI')):
        flash('Microsoft Entra ID integration is not configured.', 'error')
        return redirect(url_for('integrations.integrations'))
    state = secrets.token_urlsafe(32)
    session['entra_oauth_state'] = state
    session['entra_oauth_org'] = g.current_org.id  # bind the round trip to the org that started it
    params = requests.Request('GET', f'{AUTHORITY}/authorize', params={
        'client_id': _cfg('ENTRA_CLIENT_ID'), 'response_type': 'code', 'redirect_uri': _cfg('ENTRA_REDIRECT_URI'),
        'response_mode': 'query', 'scope': SCOPES, 'state': state, 'prompt': 'select_account'}).prepare()
    return redirect(params.url)


@entra_oauth_bp.route('/integrations/entra/callback')
@login_required
@require_permission('write')
def callback():
    state = session.pop('entra_oauth_state', None)
    org_id = session.pop('entra_oauth_org', None)
    org = g.current_org
    if (not state or not secrets.compare_digest(state.encode(), request.args.get('state', '').encode())
            or not org or org.id != org_id):
        flash('Microsoft sign-in failed (invalid state). Please try again.', 'error')
        return redirect(url_for('integrations.integrations'))
    if request.args.get('error') or not request.args.get('code'):
        flash('Microsoft authorization was cancelled or denied. An Entra admin must grant consent.', 'error')
        return redirect(url_for('integrations.integrations'))

    try:
        tok = _token_request({'grant_type': 'authorization_code', 'code': request.args['code'],
                              'redirect_uri': _cfg('ENTRA_REDIRECT_URI')})
        claims = _claims(tok['id_token'])
    except Exception:
        current_app.logger.exception('Entra token exchange failed')
        flash('Microsoft authorization failed.', 'error')
        return redirect(url_for('integrations.integrations'))

    # A tenant may be linked to only one organization, so one org can't read another's directory.
    tenant_id = claims['tid']
    taken = EntraConnection.query.filter(EntraConnection.tenant_id == tenant_id,
                                         EntraConnection.organization_id != org.id).first()
    if taken:
        flash('That Microsoft tenant is already connected to another organization.', 'error')
        return redirect(url_for('integrations.integrations'))

    upn = claims.get('preferred_username') or claims.get('email') or ''
    conn = EntraConnection.query.filter_by(organization_id=org.id).first()
    if not conn:
        conn = EntraConnection(organization_id=org.id)
        db.session.add(conn)
    conn.tenant_id = tenant_id
    conn.account = upn
    conn.domain = upn.split('@')[-1] if '@' in upn else None
    conn.access_token = encrypt(tok['access_token'])
    conn.refresh_token = encrypt(tok.get('refresh_token')) or conn.refresh_token
    conn.token_expiry = datetime.utcnow() + timedelta(seconds=int(tok.get('expires_in', 3600)))
    conn.connected_by_id = current_user.id
    conn.connected_at = datetime.utcnow()
    db.session.commit()
    flash(f'Connected to Microsoft Entra ID as {upn}.', 'success')
    return redirect(url_for('integrations.integrations'))


@entra_oauth_bp.route('/integrations/entra/disconnect', methods=['POST'])
@login_required
@require_permission('write')
def disconnect():
    if g.current_org:
        EntraConnection.query.filter_by(organization_id=g.current_org.id).delete()
        db.session.commit()
    flash('Microsoft Entra ID disconnected.', 'info')
    return redirect(url_for('integrations.integrations'))


@entra_oauth_bp.route('/integrations/entra/sync', methods=['POST'])
@login_required
@require_permission('write')
def sync_employees():
    org = g.current_org
    conn = EntraConnection.query.filter_by(organization_id=org.id).first() if org else None
    if not conn:
        flash('Connect Microsoft Entra ID first.', 'error')
        return redirect(url_for('integrations.integrations'))

    users = []
    try:
        headers = {'Authorization': f'Bearer {_access_token(conn)}'}
        url = GRAPH_USERS
        while url:
            r = requests.get(url, headers=headers, timeout=TIMEOUT)
            r.raise_for_status()
            body = r.json()
            users += body.get('value', [])
            url = body.get('@odata.nextLink')
    except requests.HTTPError as e:
        current_app.logger.exception('Entra directory sync failed')
        code = e.response.status_code if e.response is not None else 0
        flash('Microsoft is throttling or unavailable; try again shortly.' if code in (429, 500, 502, 503, 504)
              else 'Could not read the Entra directory. An Entra admin must consent to User.Read.All; try reconnecting.', 'error')
        return redirect(url_for('integrations.integrations'))
    except Exception:
        current_app.logger.exception('Entra directory sync failed')
        flash('Could not read the Entra directory. Try reconnecting.', 'error')
        return redirect(url_for('integrations.integrations'))

    created = updated = 0
    for u in users:
        if u.get('userType') == 'Guest':
            continue
        email = (u.get('mail') or u.get('userPrincipalName') or '').lower()
        if not email:
            continue
        name = u.get('displayName') or email
        status = 'Active' if u.get('accountEnabled', True) else 'Suspended'
        emp = Employee.query.filter(Employee.organization_id == org.id, func.lower(Employee.email) == email).first()
        if emp:
            # Only flip Active<->Suspended; never resurrect an HR-set Offboarded/Offboarding status.
            if emp.status in ('Active', 'Suspended'):
                emp.status = status
            updated += 1
        else:
            db.session.add(Employee(organization_id=org.id, name=name, email=email,
                                    source='Microsoft Entra ID', status=status))
            created += 1
    conn.last_synced_at = datetime.utcnow()
    db.session.commit()
    flash(f'Synced {created + updated} employee(s) from Microsoft Entra ID ({created} new, {updated} updated).', 'success')
    return redirect(url_for('integrations.integrations'))
