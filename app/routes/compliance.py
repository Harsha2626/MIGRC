from flask import Blueprint, render_template
from app.models import Framework

compliance_bp = Blueprint('compliance', __name__)


@compliance_bp.route('/compliance')
def compliance():
    frameworks = Framework.query.all()
    return render_template('compliance.html', page='compliance',
        frameworks=[fw.to_dict() for fw in frameworks])
