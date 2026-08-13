from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Vendor

vendors_bp = Blueprint('vendors', __name__)

RISK_TIER_MIDPOINTS = {'Critical': 90, 'High': 70, 'Medium': 50, 'Low': 20}


@vendors_bp.route('/vendors')
@login_required
def vendors():
    all_vendors = Vendor.query.all()
    return render_template('vendors.html', page='vendors', vendors=all_vendors,
        vendor_dicts=[v.to_dict() for v in all_vendors])


@vendors_bp.route('/vendors/add', methods=['POST'])
@login_required
def add_vendor():
    name = request.form.get('name', '').strip()
    risk_tier = request.form.get('risk_tier', 'Medium')

    if not name:
        flash('Vendor name is required.', 'error')
        return redirect(url_for('vendors.vendors'))

    if risk_tier not in RISK_TIER_MIDPOINTS:
        risk_tier = 'Medium'

    today = datetime.utcnow().date()
    vendor = Vendor(
        name=name,
        category=request.form.get('category', ''),
        risk_tier=risk_tier,
        risk_score=RISK_TIER_MIDPOINTS[risk_tier],
        status='Under Review',
        contact_name=request.form.get('contact_name', ''),
        contact_email=request.form.get('contact_email', ''),
        last_assessment=today.strftime('%Y-%m-%d'),
        next_assessment=(today + timedelta(days=180)).strftime('%Y-%m-%d'),
        compliance=request.form.getlist('compliance'),
    )
    db.session.add(vendor)
    db.session.commit()

    flash(f'Vendor "{name}" added.', 'success')
    return redirect(url_for('vendors.vendors'))


@vendors_bp.route('/vendors/<int:vendor_id>/edit', methods=['POST'])
@login_required
def edit_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    name = request.form.get('name', '').strip()
    risk_tier = request.form.get('risk_tier', vendor.risk_tier)

    if not name:
        flash('Vendor name is required.', 'error')
        return redirect(url_for('vendors.vendors'))

    if risk_tier not in RISK_TIER_MIDPOINTS:
        risk_tier = vendor.risk_tier

    vendor.name = name
    vendor.category = request.form.get('category', vendor.category)
    vendor.risk_tier = risk_tier
    vendor.risk_score = RISK_TIER_MIDPOINTS[risk_tier]
    vendor.status = request.form.get('status', vendor.status)
    vendor.contact_name = request.form.get('contact_name', vendor.contact_name)
    vendor.contact_email = request.form.get('contact_email', vendor.contact_email)
    vendor.compliance = request.form.getlist('compliance') or vendor.compliance

    db.session.commit()
    flash(f'Vendor "{name}" updated.', 'success')
    return redirect(url_for('vendors.vendors'))


@vendors_bp.route('/vendors/<int:vendor_id>/delete', methods=['POST'])
@login_required
def delete_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    name = vendor.name
    db.session.delete(vendor)
    db.session.commit()
    flash(f'Vendor "{name}" deleted.', 'info')
    return redirect(url_for('vendors.vendors'))
