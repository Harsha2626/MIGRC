from flask import Blueprint, render_template
from flask_login import login_required

integrations_bp = Blueprint('integrations', __name__)


@integrations_bp.route('/integrations')
@login_required
def integrations():
    return render_template('integrations.html', page='integrations')
