from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Asset
from app.services.activity import log_activity
from app.services.csv_export import csv_response
from app.utils import require_permission

assets_bp = Blueprint('assets', __name__)


@assets_bp.route('/assets')
@login_required
def assets():
    all_assets = Asset.query.all()
    return render_template('assets.html', page='assets', assets=all_assets,
        asset_dicts=[a.to_dict() for a in all_assets])


@assets_bp.route('/assets/add', methods=['POST'])
@login_required
@require_permission('write')
def add_asset():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Asset name is required.', 'error')
        return redirect(url_for('assets.assets'))

    asset = Asset(
        name=name,
        type=request.form.get('type', ''),
        environment=request.form.get('environment', ''),
        owner=request.form.get('owner', ''),
        classification=request.form.get('classification', ''),
        status='Active',
        cloud_provider=request.form.get('cloud_provider', ''),
    )
    db.session.add(asset)
    log_activity('created', 'Asset', name)
    db.session.commit()

    flash(f'Asset "{name}" added.', 'success')
    return redirect(url_for('assets.assets'))


@assets_bp.route('/assets/<int:asset_id>/edit', methods=['POST'])
@login_required
@require_permission('write')
def edit_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    name = request.form.get('name', '').strip()
    if not name:
        flash('Asset name is required.', 'error')
        return redirect(url_for('assets.assets'))

    asset.name = name
    asset.type = request.form.get('type', asset.type)
    asset.environment = request.form.get('environment', asset.environment)
    asset.owner = request.form.get('owner', asset.owner)
    asset.classification = request.form.get('classification', asset.classification)
    asset.status = request.form.get('status', asset.status)
    asset.cloud_provider = request.form.get('cloud_provider', asset.cloud_provider)

    log_activity('updated', 'Asset', name)
    db.session.commit()
    flash(f'Asset "{name}" updated.', 'success')
    return redirect(url_for('assets.assets'))


@assets_bp.route('/assets/export')
@login_required
def export_assets():
    rows = [(a.name, a.type, a.environment, a.owner, a.classification, a.status, a.cloud_provider) for a in Asset.query.all()]
    return csv_response('assets.csv', ['Name', 'Type', 'Environment', 'Owner', 'Classification', 'Status', 'Cloud Provider'], rows)


@assets_bp.route('/assets/<int:asset_id>/delete', methods=['POST'])
@login_required
@require_permission('delete')
def delete_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    name = asset.name
    db.session.delete(asset)
    log_activity('deleted', 'Asset', name)
    db.session.commit()
    flash(f'Asset "{name}" deleted.', 'info')
    return redirect(url_for('assets.assets'))
