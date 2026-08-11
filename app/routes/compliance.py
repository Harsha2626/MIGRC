from flask import Blueprint, render_template, abort
from flask_login import login_required
from app.models import Framework, Control

compliance_bp = Blueprint('compliance', __name__)


@compliance_bp.route('/compliance')
@login_required
def compliance():
    frameworks = Framework.query.all()
    return render_template('compliance.html', page='compliance',
        frameworks=[fw.to_dict() for fw in frameworks])


@compliance_bp.route('/compliance/<int:framework_id>')
@login_required
def framework_detail(framework_id):
    fw = Framework.query.get_or_404(framework_id)
    controls = Control.query.filter_by(framework_id=fw.id).order_by(Control.code).all()

    # Group controls by category
    categories = {}
    for c in controls:
        cat = c.category or 'Uncategorized'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(c)

    return render_template('compliance_detail.html', page='compliance',
        framework=fw, controls=controls, categories=categories)
