from flask import Blueprint, render_template, jsonify
from app.models import Risk

risks_bp = Blueprint('risks', __name__)


@risks_bp.route('/risks')
def risks():
    all_risks = Risk.query.order_by(Risk.score.desc()).all()
    # Template uses {{ risks|tojson }} for JS risk matrix, so pass dicts
    risk_dicts = [r.to_dict() for r in all_risks]
    return render_template('risks.html', page='risks', risks=risk_dicts)


@risks_bp.route('/api/risks/matrix')
def api_risk_matrix():
    matrix = {
        "Critical": {"High": 0, "Medium": 0, "Low": 0},
        "High": {"High": 0, "Medium": 0, "Low": 0},
        "Medium": {"High": 0, "Medium": 0, "Low": 0},
        "Low": {"High": 0, "Medium": 0, "Low": 0},
    }
    for r in Risk.query.all():
        if r.impact in matrix and r.likelihood in matrix[r.impact]:
            matrix[r.impact][r.likelihood] += 1
    return jsonify(matrix)
