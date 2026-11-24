import json
from datetime import datetime

from flask import Blueprint, redirect, url_for, flash, request, g, current_app
from flask_login import login_required, current_user

from app.integrations import registry
from app.models import db, IntegrationConnection
from app.services.crypto import encrypt
from app.services.integration_scans import known_providers, run_scan
from app.utils import require_permission

scans_bp = Blueprint('scans', __name__)


def _back():
    return redirect(url_for('integrations.integrations'))


@scans_bp.route('/integrations/<provider>/scan', methods=['POST'])
@login_required
@require_permission('write')
def scan(provider):
    if provider not in known_providers() or not g.current_org:
        flash('Unknown integration.', 'error')
        return _back()
    try:
        total, failed, mapped, risks = run_scan(g.current_org, provider)
        flash(f'Scan complete: {total} checks, {failed} failed. {mapped} new control mapping(s), {risks} new risk(s). '
              'Review AI suggestions under Compliance.', 'warning' if failed else 'success')
    except LookupError:
        flash('Connect this integration first.', 'error')
    except Exception:
        current_app.logger.exception('scan failed')
        flash('Scan failed. Check the connection credentials and their read permissions.', 'error')
    return _back()


@scans_bp.route('/integrations/p/<provider>/connect', methods=['POST'])
@login_required
@require_permission('write')
def connect(provider):
    spec, org = registry().get(provider), g.current_org
    if not spec or not org:
        flash('Unknown integration.', 'error')
        return _back()
    cfg = {f['name']: request.form.get(f['name'], '').strip() for f in spec['fields']}
    if not all(cfg.values()):
        flash(f"Fill in every {spec['name']} field.", 'error')
        return _back()
    try:
        label = spec['validate'](cfg)
    except Exception:
        current_app.logger.exception('%s credential validation failed', provider)
        flash(f"{spec['name']} rejected those credentials or they lack read access.", 'error')
        return _back()
    conn = IntegrationConnection.query.filter_by(organization_id=org.id, provider=provider).first()
    if not conn:
        conn = IntegrationConnection(organization_id=org.id, provider=provider)
        db.session.add(conn)
    conn.config, conn.account_label = encrypt(json.dumps(cfg)), (label or '')[:255]
    conn.connected_by_id, conn.connected_at = current_user.id, datetime.utcnow()
    db.session.commit()
    flash(f"Connected {spec['name']}. Run a scan to collect evidence.", 'success')
    return _back()


@scans_bp.route('/integrations/p/<provider>/disconnect', methods=['POST'])
@login_required
@require_permission('write')
def disconnect(provider):
    if g.current_org:
        IntegrationConnection.query.filter_by(organization_id=g.current_org.id, provider=provider).delete()
        db.session.commit()
    flash('Integration disconnected. Evidence and risks already created are kept.', 'info')
    return _back()
