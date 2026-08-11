from flask import Blueprint, render_template
from flask_login import login_required
from app.models import Asset

assets_bp = Blueprint('assets', __name__)


@assets_bp.route('/assets')
@login_required
def assets():
    all_assets = Asset.query.all()
    return render_template('assets.html', page='assets', assets=all_assets)
