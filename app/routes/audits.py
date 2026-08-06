from flask import Blueprint, render_template
from app.models import Audit

audits_bp = Blueprint('audits', __name__)


@audits_bp.route('/audits')
def audits():
    all_audits = Audit.query.all()
    # Template uses {{ audits|tojson }}, so pass dicts for JSON serialization
    audit_dicts = [a.to_dict() for a in all_audits]
    return render_template('audits.html', page='audits', audits=audit_dicts)
