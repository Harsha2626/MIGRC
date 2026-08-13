from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.models import db, Risk

risks_bp = Blueprint('risks', __name__)

RISK_LEVEL_SCORES = {'Critical': 5, 'High': 4, 'Medium': 3, 'Low': 2, 'Negligible': 1}


@risks_bp.route('/risks')
@login_required
def risks():
    all_risks = Risk.query.order_by(Risk.score.desc()).all()
    # Template uses {{ risks|tojson }} for JS risk matrix, so pass dicts
    risk_dicts = [r.to_dict() for r in all_risks]
    return render_template('risks.html', page='risks', risks=risk_dicts)


@risks_bp.route('/risks/add', methods=['POST'])
@login_required
def add_risk():
    title = request.form.get('title', '').strip()
    likelihood = request.form.get('likelihood', 'Medium')
    impact = request.form.get('impact', 'Medium')

    if not title:
        flash('Risk title is required.', 'error')
        return redirect(url_for('risks.risks'))

    if likelihood not in RISK_LEVEL_SCORES or impact not in RISK_LEVEL_SCORES:
        flash('Invalid likelihood or impact level.', 'error')
        return redirect(url_for('risks.risks'))

    risk = Risk(
        title=title,
        description=request.form.get('description', ''),
        category=request.form.get('category', ''),
        likelihood=likelihood,
        impact=impact,
        score=RISK_LEVEL_SCORES[likelihood] * RISK_LEVEL_SCORES[impact],
        owner=request.form.get('owner', ''),
        status='Open',
        treatment=request.form.get('treatment', 'Mitigate'),
        created=datetime.utcnow().strftime('%Y-%m-%d'),
    )
    db.session.add(risk)
    db.session.commit()

    flash(f'Risk "{title}" added.', 'success')
    return redirect(url_for('risks.risks'))


@risks_bp.route('/risks/<int:risk_id>/edit', methods=['POST'])
@login_required
def edit_risk(risk_id):
    risk = Risk.query.get_or_404(risk_id)
    title = request.form.get('title', '').strip()
    likelihood = request.form.get('likelihood', risk.likelihood)
    impact = request.form.get('impact', risk.impact)

    if not title:
        flash('Risk title is required.', 'error')
        return redirect(url_for('risks.risks'))

    if likelihood not in RISK_LEVEL_SCORES or impact not in RISK_LEVEL_SCORES:
        flash('Invalid likelihood or impact level.', 'error')
        return redirect(url_for('risks.risks'))

    risk.title = title
    risk.description = request.form.get('description', risk.description)
    risk.category = request.form.get('category', risk.category)
    risk.likelihood = likelihood
    risk.impact = impact
    risk.score = RISK_LEVEL_SCORES[likelihood] * RISK_LEVEL_SCORES[impact]
    risk.owner = request.form.get('owner', risk.owner)
    risk.status = request.form.get('status', risk.status)
    risk.treatment = request.form.get('treatment', risk.treatment)

    db.session.commit()
    flash(f'Risk "{title}" updated.', 'success')
    return redirect(url_for('risks.risks'))


@risks_bp.route('/risks/<int:risk_id>/delete', methods=['POST'])
@login_required
def delete_risk(risk_id):
    risk = Risk.query.get_or_404(risk_id)
    title = risk.title
    db.session.delete(risk)
    db.session.commit()
    flash(f'Risk "{title}" deleted.', 'info')
    return redirect(url_for('risks.risks'))


@risks_bp.route('/api/risks/matrix')
@login_required
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
