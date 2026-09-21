from datetime import datetime
from flask import Blueprint, redirect, url_for, flash, request, session, g, current_app
from flask_login import login_required, current_user
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.models import db, GoogleWorkspaceConnection, Employee
from app.utils import require_permission

google_oauth_bp = Blueprint('google_oauth', __name__)

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/admin.directory.user.readonly',
]


def _flow():
    client_config = {
        "web": {
            "client_id": current_app.config['GOOGLE_CLIENT_ID'],
            "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [current_app.config['GOOGLE_REDIRECT_URI']],
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=current_app.config['GOOGLE_REDIRECT_URI'])


def _credentials_for(conn):
    return Credentials(
        token=conn.access_token,
        refresh_token=conn.refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=current_app.config['GOOGLE_CLIENT_ID'],
        client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
        scopes=SCOPES,
    )


@google_oauth_bp.route('/integrations/google/connect')
@login_required
@require_permission('write')
def connect():
    if not current_app.config.get('GOOGLE_CLIENT_ID'):
        flash('Google integration is not configured.', 'error')
        return redirect(url_for('setup.setup_wizard'))

    flow = _flow()
    auth_url, state = flow.authorization_url(
        access_type='offline', include_granted_scopes='true', prompt='consent')
    session['google_oauth_state'] = state
    return redirect(auth_url)


@google_oauth_bp.route('/integrations/google/callback')
def callback():
    state = session.pop('google_oauth_state', None)
    if not state or state != request.args.get('state'):
        flash('Google sign-in failed (invalid state). Please try again.', 'error')
        return redirect(url_for('setup.setup_wizard'))

    org = g.current_org
    if not org:
        flash('No active organization.', 'error')
        return redirect(url_for('setup.setup_wizard'))

    flow = _flow()
    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception as e:
        current_app.logger.exception("Google OAuth token fetch failed: %s", e)
        flash('Google authorization was cancelled or failed.', 'error')
        return redirect(url_for('setup.setup_wizard'))

    creds = flow.credentials
    userinfo = build('oauth2', 'v2', credentials=creds).userinfo().get().execute()
    email = userinfo.get('email', '')
    domain = email.split('@')[-1] if '@' in email else None

    conn = GoogleWorkspaceConnection.query.filter_by(organization_id=org.id).first()
    if not conn:
        conn = GoogleWorkspaceConnection(organization_id=org.id)
        db.session.add(conn)

    conn.google_email = email
    conn.domain = domain
    conn.access_token = creds.token
    conn.refresh_token = creds.refresh_token or conn.refresh_token
    conn.token_expiry = creds.expiry
    conn.connected_by_id = current_user.id
    conn.connected_at = datetime.utcnow()
    db.session.commit()

    flash(f'Connected to Google Workspace as {email}.', 'success')
    return redirect(url_for('setup.setup_wizard'))


@google_oauth_bp.route('/integrations/google/disconnect', methods=['POST'])
@login_required
@require_permission('write')
def disconnect():
    org = g.current_org
    if org:
        GoogleWorkspaceConnection.query.filter_by(organization_id=org.id).delete()
        db.session.commit()
    flash('Google Workspace disconnected.', 'info')
    return redirect(url_for('setup.setup_wizard'))


@google_oauth_bp.route('/integrations/google/sync', methods=['POST'])
@login_required
@require_permission('write')
def sync_employees():
    org = g.current_org
    conn = GoogleWorkspaceConnection.query.filter_by(organization_id=org.id).first() if org else None
    if not conn:
        flash('Connect Google Workspace first.', 'error')
        return redirect(url_for('setup.setup_wizard'))

    creds = _credentials_for(conn)
    try:
        service = build('admin', 'directory_v1', credentials=creds)
        results = service.users().list(customer='my_customer', maxResults=500, orderBy='email').execute()
    except Exception:
        flash('Could not reach Google Directory. This requires the connecting account to be a Workspace admin — try reconnecting.', 'error')
        return redirect(url_for('setup.setup_wizard'))

    # Credentials may have silently refreshed its access token during the call above;
    # persist whatever it's holding now so the next sync doesn't need a fresh login.
    conn.access_token = creds.token
    conn.last_synced_at = datetime.utcnow()

    users = results.get('users', [])
    created, updated = 0, 0
    for u in users:
        email = u.get('primaryEmail', '')
        if not email:
            continue
        name = (u.get('name') or {}).get('fullName') or email
        status = 'Suspended' if u.get('suspended') else 'Active'

        employee = Employee.query.filter_by(organization_id=org.id, email=email).first()
        if employee:
            employee.name = name
            employee.status = status
            updated += 1
        else:
            db.session.add(Employee(
                organization_id=org.id, name=name, email=email,
                source='Google Workspace', status=status,
            ))
            created += 1

    db.session.commit()
    flash(f'Synced {len(users)} employee(s) from Google Workspace ({created} new, {updated} updated).', 'success')
    return redirect(url_for('setup.setup_wizard'))
