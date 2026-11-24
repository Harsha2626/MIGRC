"""Jira Cloud integration: push a risk to Jira as an issue (remediation ticket).

Each org supplies site URL (https://<site>.atlassian.net), account email, API token and a project key.
The token is stored Fernet-encrypted. Auth is HTTP Basic (email:token).
"""
import re
from datetime import datetime

import requests
from flask import Blueprint, redirect, url_for, flash, request, g, current_app
from flask_login import login_required, current_user

from app.models import db, JiraConnection, Risk
from app.services.crypto import encrypt, decrypt
from app.utils import require_permission

jira_bp = Blueprint('jira', __name__)

TIMEOUT = 20
# shortcut: Jira Cloud only (also blocks SSRF to arbitrary hosts); add Data Center support when asked.
SITE_RE = re.compile(r'^https://[a-z0-9-]+\.atlassian\.net$')
KEY_RE = re.compile(r'^[A-Z][A-Z0-9_]{1,19}$')


def _back():
    return redirect(url_for('integrations.integrations'))


def _call(conn_or_vals, method, path, **kw):
    site, email, token = conn_or_vals
    r = requests.request(method, f'{site}/rest/api/3/{path}', auth=(email, token),
                         headers={'Accept': 'application/json'}, timeout=TIMEOUT, allow_redirects=False, **kw)
    r.raise_for_status()
    return r.json()


def _adf(text):
    """Jira v3 requires Atlassian Document Format for rich text fields."""
    paras = [p for p in (text or '').split('\n') if p.strip()] or ['-']
    return {'type': 'doc', 'version': 1,
            'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': p}]} for p in paras]}


@jira_bp.route('/integrations/jira/connect', methods=['POST'])
@login_required
@require_permission('write')
def connect():
    org = g.current_org
    site = request.form.get('site_url', '').strip().rstrip('/').lower()
    email = request.form.get('email', '').strip()
    token = request.form.get('api_token', '').strip()
    project = request.form.get('project_key', '').strip().upper()
    if not org or not SITE_RE.match(site) or not email or not token or not KEY_RE.match(project):
        flash('Enter your https://<site>.atlassian.net URL, account email, API token and project key.', 'error')
        return _back()
    try:
        _call((site, email, token), 'GET', f'project/{project}')  # validates creds and project access together
    except Exception:
        current_app.logger.exception('Jira credential validation failed')
        flash('Jira rejected those credentials or the project key.', 'error')
        return _back()

    conn = JiraConnection.query.filter_by(organization_id=org.id).first()
    if not conn:
        conn = JiraConnection(organization_id=org.id)
        db.session.add(conn)
    conn.site_url, conn.email, conn.api_token, conn.project_key = site, email, encrypt(token), project
    conn.connected_by_id = current_user.id
    conn.connected_at = datetime.utcnow()
    db.session.commit()
    flash(f'Connected to Jira project {project}.', 'success')
    return _back()


@jira_bp.route('/integrations/jira/disconnect', methods=['POST'])
@login_required
@require_permission('write')
def disconnect():
    if g.current_org:
        JiraConnection.query.filter_by(organization_id=g.current_org.id).delete()
        db.session.commit()
    flash('Jira disconnected. Existing issue links on risks are kept.', 'info')
    return _back()


@jira_bp.route('/risks/<int:risk_id>/jira', methods=['POST'])
@login_required
@require_permission('write')
def create_issue(risk_id):
    org = g.current_org
    risk = Risk.query.filter_by(id=risk_id, organization_id=org.id if org else -1).first_or_404()
    back = redirect(url_for('risks.risk_detail', risk_id=risk.id))
    conn = JiraConnection.query.filter_by(organization_id=org.id).first()
    if not conn:
        flash('Connect Jira first (Integrations page).', 'error')
        return back
    if risk.jira_key:
        flash(f'Already linked to {risk.jira_key}.', 'info')
        return back
    desc = (f'{risk.description or ""}\n'
            f'Category: {risk.category or "-"} | Likelihood: {risk.likelihood or "-"} | '
            f'Impact: {risk.impact or "-"} | Score: {risk.score or "-"}\n'
            f'Treatment plan: {risk.treatment_plan or "-"}')
    try:
        data = _call((conn.site_url, conn.email, decrypt(conn.api_token)), 'POST', 'issue', json={'fields': {
            'project': {'key': conn.project_key}, 'issuetype': {'name': 'Task'},
            'summary': f'[Risk] {risk.title}'[:255], 'description': _adf(desc)}})
    except Exception:
        current_app.logger.exception('Jira issue creation failed')
        flash('Could not create the Jira issue (check the project allows a "Task" issue type).', 'error')
        return back
    risk.jira_key = data['key']
    db.session.commit()
    flash(f'Created Jira issue {risk.jira_key}.', 'success')
    return back
