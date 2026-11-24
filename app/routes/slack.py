"""Slack integration: employee directory sync (users.list) and notification posting (chat.postMessage).

Each org supplies a Bot User OAuth Token (xoxb-...) and an alert channel. We validate with auth.test,
store the token Fernet-encrypted, import workspace members as Employees, and mirror notifications to the channel.
"""
from datetime import datetime

import requests
from flask import Blueprint, redirect, url_for, flash, request, g, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from app.models import db, SlackConnection, Employee
from app.services.crypto import encrypt, decrypt
from app.utils import require_permission

slack_bp = Blueprint('slack', __name__)

API = 'https://slack.com/api/'
TIMEOUT = 20


def _back():
    return redirect(url_for('integrations.integrations'))


def _call(token, method, **params):
    """Slack returns HTTP 200 with ok=false on errors, so check the body. Raises on failure."""
    r = requests.post(API + method, data=params, headers={'Authorization': f'Bearer {token}'},
                      timeout=TIMEOUT, allow_redirects=False)
    r.raise_for_status()
    data = r.json()
    if not data.get('ok'):
        raise RuntimeError(f"Slack {method}: {data.get('error')}")
    return data


def post_to_slack(org_id, text):
    """Best-effort post to the org's alert channel. Never raises (must not break the caller)."""
    try:
        conn = SlackConnection.query.filter_by(organization_id=org_id).first()
        if conn and conn.channel:
            _call(decrypt(conn.bot_token), 'chat.postMessage', channel=conn.channel, text=text)
    except Exception:
        current_app.logger.exception('Slack post failed')


@slack_bp.route('/integrations/slack/connect', methods=['POST'])
@login_required
@require_permission('write')
def connect():
    org = g.current_org
    token = request.form.get('bot_token', '').strip()
    channel = request.form.get('channel', '').strip().lstrip('#')
    if not org or not token.startswith('xoxb-') or not channel:
        flash('Enter a Bot User OAuth Token (xoxb-...) and an alert channel ID or name.', 'error')
        return _back()
    try:
        auth = _call(token, 'auth.test')
        # Fail now if the bot can't post (not invited / missing chat:write) rather than silently later.
        _call(token, 'chat.postMessage', channel=channel, text='MIGRC connected to this channel.')
    except Exception:
        current_app.logger.exception('Slack credential validation failed')
        flash('Slack rejected that token or channel (invite the bot to the channel and grant chat:write).', 'error')
        return _back()

    conn = SlackConnection.query.filter_by(organization_id=org.id).first()
    if not conn:
        conn = SlackConnection(organization_id=org.id)
        db.session.add(conn)
    conn.team_id, conn.team_name = auth.get('team_id'), auth.get('team')
    conn.bot_token, conn.channel = encrypt(token), channel
    conn.connected_by_id = current_user.id
    conn.connected_at = datetime.utcnow()
    db.session.commit()
    flash(f"Connected to Slack ({auth.get('team')}).", 'success')
    return _back()


@slack_bp.route('/integrations/slack/disconnect', methods=['POST'])
@login_required
@require_permission('write')
def disconnect():
    if g.current_org:
        SlackConnection.query.filter_by(organization_id=g.current_org.id).delete()
        db.session.commit()
    flash('Slack disconnected.', 'info')
    return _back()


@slack_bp.route('/integrations/slack/sync', methods=['POST'])
@login_required
@require_permission('write')
def sync_employees():
    org = g.current_org
    conn = SlackConnection.query.filter_by(organization_id=org.id).first() if org else None
    if not conn:
        flash('Connect Slack first.', 'error')
        return _back()
    members, cursor = [], ''
    try:
        token = decrypt(conn.bot_token)
        while True:
            data = _call(token, 'users.list', limit=200, cursor=cursor)
            members += data.get('members', [])
            cursor = (data.get('response_metadata') or {}).get('next_cursor')
            if not cursor:
                break
    except Exception:
        current_app.logger.exception('Slack directory sync failed')
        flash('Could not read the Slack directory (the bot needs users:read and users:read.email).', 'error')
        return _back()

    created = updated = 0
    for m in members:
        p = m.get('profile') or {}
        email = (p.get('email') or '').lower()
        if not email or m.get('is_bot') or m.get('id') == 'USLACKBOT' or m.get('is_restricted'):
            continue  # skip bots and guests; no email means no way to match an Employee
        name = (m.get('real_name') or p.get('real_name') or email)[:100]
        status = 'Suspended' if m.get('deleted') else 'Active'
        emp = Employee.query.filter(Employee.organization_id == org.id, func.lower(Employee.email) == email).first()
        if emp:
            # Only flip Active<->Suspended; never resurrect an HR-set Offboarded/Offboarding status.
            if emp.status in ('Active', 'Suspended'):
                emp.status = status
            updated += 1
        else:
            db.session.add(Employee(organization_id=org.id, name=name, email=email, source='Slack', status=status))
            created += 1
    conn.last_synced_at = datetime.utcnow()
    db.session.commit()
    flash(f'Synced {created + updated} employee(s) from Slack ({created} new, {updated} updated).', 'success')
    return _back()
