from flask import Blueprint, render_template
from app.models import Vendor

vendors_bp = Blueprint('vendors', __name__)


@vendors_bp.route('/vendors')
def vendors():
    all_vendors = Vendor.query.all()
    return render_template('vendors.html', page='vendors', vendors=all_vendors)
