from flask import Blueprint, render_template
from app.models import Asset

assets_bp = Blueprint('assets', __name__)


@assets_bp.route('/assets')
def assets():
    all_assets = Asset.query.all()
    return render_template('assets.html', page='assets', assets=all_assets)
