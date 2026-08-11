from flask import Blueprint, render_template
from flask_login import login_required
from app.models import Policy

policies_bp = Blueprint('policies', __name__)


@policies_bp.route('/policies')
@login_required
def policies():
    all_policies = Policy.query.all()
    return render_template('policies.html', page='policies', policies=all_policies)
