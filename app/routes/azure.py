"""Microsoft Azure cloud-provider integration: asset inventory via Azure Resource Manager.

Each org supplies its own read-only service principal (tenant id, client id, client secret,
subscription id). We validate it with a client-credentials token + a subscription GET, store the
secret Fernet-encrypted, and import the subscription's resources as Assets (cloud_provider='Azure').
"""
import re
from datetime import datetime

import requests
from flask import Blueprint, redirect, url_for, flash, request, g, current_app
from flask_login import login_required, current_user

from app.models import db, AzureConnection, Asset
from app.services.crypto import encrypt, decrypt
from app.utils import require_permission

azure_bp = Blueprint('azure', __name__)

ARM = 'https://management.azure.com'
TIMEOUT = 20
GUID = re.compile(r'^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$')


def _token(tenant_id, client_id, client_secret):
    r = requests.post(f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token', timeout=TIMEOUT, data={
        'grant_type': 'client_credentials', 'client_id': client_id, 'client_secret': client_secret,
        'scope': f'{ARM}/.default'})
    r.raise_for_status()
    return r.json()['access_token']


def _back():
    return redirect(url_for('integrations.integrations'))


@azure_bp.route('/integrations/azure/connect', methods=['POST'])
@login_required
@require_permission('write')
def connect():
    org = g.current_org
    f = {k: request.form.get(k, '').strip() for k in ('tenant_id', 'client_id', 'client_secret', 'subscription_id')}
    if not org or not all(f.values()) or not all(GUID.match(f[k]) for k in ('tenant_id', 'client_id', 'subscription_id')):
        flash('Enter a valid Tenant ID, Client ID, Subscription ID (GUIDs) and Client Secret.', 'error')
        return _back()
    try:
        tok = _token(f['tenant_id'], f['client_id'], f['client_secret'])
        r = requests.get(f"{ARM}/subscriptions/{f['subscription_id']}?api-version=2022-12-01",
                         headers={'Authorization': f'Bearer {tok}'}, timeout=TIMEOUT)
        r.raise_for_status()
        sub_name = r.json().get('displayName')
    except Exception:
        current_app.logger.exception('Azure credential validation failed')
        flash('Azure rejected those credentials, or the service principal has no access to that subscription '
              '(needs the Reader role).', 'error')
        return _back()

    conn = AzureConnection.query.filter_by(organization_id=org.id).first()
    if not conn:
        conn = AzureConnection(organization_id=org.id)
        db.session.add(conn)
    conn.tenant_id, conn.client_id, conn.subscription_id = f['tenant_id'], f['client_id'], f['subscription_id']
    conn.client_secret = encrypt(f['client_secret'])
    conn.subscription_name = sub_name
    conn.connected_by_id = current_user.id
    conn.connected_at = datetime.utcnow()
    db.session.commit()
    flash(f'Connected to Azure subscription {sub_name or f["subscription_id"]}.', 'success')
    return _back()


@azure_bp.route('/integrations/azure/disconnect', methods=['POST'])
@login_required
@require_permission('write')
def disconnect():
    if g.current_org:
        AzureConnection.query.filter_by(organization_id=g.current_org.id).delete()
        db.session.commit()
    flash('Microsoft Azure disconnected.', 'info')
    return _back()


@azure_bp.route('/integrations/azure/sync', methods=['POST'])
@login_required
@require_permission('write')
def sync_assets():
    org = g.current_org
    conn = AzureConnection.query.filter_by(organization_id=org.id).first() if org else None
    if not conn:
        flash('Connect Microsoft Azure first.', 'error')
        return _back()
    resources = []
    try:
        headers = {'Authorization': f'Bearer {_token(conn.tenant_id, conn.client_id, decrypt(conn.client_secret))}'}
        url = f'{ARM}/subscriptions/{conn.subscription_id}/resources?api-version=2021-04-01'
        while url:
            r = requests.get(url, headers=headers, timeout=TIMEOUT)
            r.raise_for_status()
            body = r.json()
            resources += body.get('value', [])
            url = body.get('nextLink')
    except Exception:
        current_app.logger.exception('Azure asset sync failed')
        flash('Could not read Azure resources. Check the secret has not expired and the Reader role is still assigned.', 'error')
        return _back()

    existing = {a.resource_id: a for a in Asset.query.filter_by(organization_id=org.id, cloud_provider='Azure')}
    created = updated = 0
    for res in resources:
        rid = res['id'][:300]  # shortcut: ids >300 chars truncate; widen Asset.resource_id if that ever collides
        asset = existing.get(rid)
        if asset:
            asset.name, asset.type, asset.region = res.get('name', rid)[:200], res.get('type', '')[:50], res.get('location')
            updated += 1
        else:
            db.session.add(Asset(organization_id=org.id, name=res.get('name', rid)[:200], type=res.get('type', '')[:50],
                                 resource_id=rid, region=(res.get('location') or '')[:50], cloud_provider='Azure'))
            created += 1
    conn.last_synced_at = datetime.utcnow()
    db.session.commit()
    flash(f'Synced {created + updated} Azure resource(s) ({created} new, {updated} updated).', 'success')
    return _back()
