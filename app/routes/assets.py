from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Asset
from app.services.activity import log_activity
from app.services.csv_export import csv_response
from app.utils import require_permission

assets_bp = Blueprint('assets', __name__)

# Asset type categories, in sidebar display order.
ASSET_TYPES = [
    'Compute Instances', 'Container Platforms', 'Storage & Databases',
    'Virtual Network (VPCs)', 'Serverless Functions', 'Monitoring & Logging',
    'Key Management', 'Mobile Devices', 'Identity Users', 'Identity Roles',
    'Identity Groups', 'Code Repo',
]


@assets_bp.route('/assets')
@login_required
def assets():
    all_assets = Asset.query.all()

    type_counts = {t: 0 for t in ASSET_TYPES}
    for a in all_assets:
        if a.type in type_counts:
            type_counts[a.type] += 1

    selected_type = request.args.get('type') or next((t for t in ASSET_TYPES if type_counts[t] > 0), ASSET_TYPES[0])
    if selected_type not in ASSET_TYPES:
        selected_type = ASSET_TYPES[0]

    filtered = [a for a in all_assets if a.type == selected_type]
    regions = sorted({a.region for a in filtered if a.region})
    sources = sorted({a.cloud_provider for a in filtered if a.cloud_provider})

    return render_template('assets.html', page='assets',
        asset_types=ASSET_TYPES, type_counts=type_counts, selected_type=selected_type,
        assets=filtered, asset_dicts=[a.to_dict() for a in filtered],
        total_assets=len(all_assets), regions=regions, sources=sources)


@assets_bp.route('/assets/add', methods=['POST'])
@login_required
@require_permission('write')
def add_asset():
    name = request.form.get('name', '').strip()
    asset_type = request.form.get('type', ASSET_TYPES[0])
    if not name:
        flash('Asset name is required.', 'error')
        return redirect(url_for('assets.assets', type=asset_type))

    asset = Asset(
        name=name,
        type=asset_type,
        resource_id=request.form.get('resource_id', '').strip(),
        region=request.form.get('region', '').strip(),
        risk_associated=request.form.get('risk_associated', '').strip(),
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
    return redirect(url_for('assets.assets', type=asset_type))


@assets_bp.route('/assets/<int:asset_id>/edit', methods=['POST'])
@login_required
@require_permission('write')
def edit_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    name = request.form.get('name', '').strip()
    if not name:
        flash('Asset name is required.', 'error')
        return redirect(url_for('assets.assets', type=asset.type))

    asset.name = name
    asset.type = request.form.get('type', asset.type)
    asset.resource_id = request.form.get('resource_id', asset.resource_id)
    asset.region = request.form.get('region', asset.region)
    asset.risk_associated = request.form.get('risk_associated', asset.risk_associated)
    asset.environment = request.form.get('environment', asset.environment)
    asset.owner = request.form.get('owner', asset.owner)
    asset.classification = request.form.get('classification', asset.classification)
    asset.status = request.form.get('status', asset.status)
    asset.cloud_provider = request.form.get('cloud_provider', asset.cloud_provider)

    log_activity('updated', 'Asset', name)
    db.session.commit()
    flash(f'Asset "{name}" updated.', 'success')
    return redirect(url_for('assets.assets', type=asset.type))


@assets_bp.route('/assets/export')
@login_required
def export_assets():
    rows = [(a.name, a.type, a.resource_id, a.region, a.risk_associated, a.environment,
              a.owner, a.classification, a.status, a.cloud_provider) for a in Asset.query.all()]
    return csv_response('assets.csv', ['Name', 'Type', 'Resource ID', 'Region', 'Risk Associated',
        'Environment', 'Owner', 'Classification', 'Status', 'Cloud Provider'], rows)


@assets_bp.route('/assets/<int:asset_id>/delete', methods=['POST'])
@login_required
@require_permission('delete')
def delete_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    name = asset.name
    asset_type = asset.type
    db.session.delete(asset)
    log_activity('deleted', 'Asset', name)
    db.session.commit()
    flash(f'Asset "{name}" deleted.', 'info')
    return redirect(url_for('assets.assets', type=asset_type))


@assets_bp.route('/assets/bulk-delete', methods=['POST'])
@login_required
@require_permission('delete')
def bulk_delete_assets():
    ids = request.form.getlist('asset_ids')
    asset_type = request.form.get('type', ASSET_TYPES[0])
    count = 0
    for aid in ids:
        asset = Asset.query.get(int(aid))
        if asset:
            db.session.delete(asset)
            count += 1
    if count:
        log_activity('deleted', 'Asset', f'{count} asset(s)')
        db.session.commit()
        flash(f'{count} asset(s) deleted.', 'info')
    return redirect(url_for('assets.assets', type=asset_type))
