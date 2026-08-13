from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Audit, AuditEvidence, Framework

audits_bp = Blueprint('audits', __name__)


@audits_bp.route('/audits')
@login_required
def audits():
    all_audits = Audit.query.all()
    frameworks = Framework.query.order_by(Framework.name).all()
    evidence_by_audit = {
        a.id: [
            {'id': ei.id, 'title': ei.control.title, 'code': ei.control.code, 'status': ei.status}
            for ei in a.evidence_items.order_by(AuditEvidence.id)
        ]
        for a in all_audits
    }
    # Template uses {{ audits|tojson }}, so pass dicts for JSON serialization
    audit_dicts = [a.to_dict() for a in all_audits]
    return render_template('audits.html', page='audits', audits=audit_dicts,
        frameworks=frameworks, evidence_by_audit=evidence_by_audit)


@audits_bp.route('/audits/add', methods=['POST'])
@login_required
def add_audit():
    name = request.form.get('name', '').strip()
    framework_id = request.form.get('framework_id')

    if not name or not framework_id:
        flash('Audit name and framework are required.', 'error')
        return redirect(url_for('audits.audits'))

    framework = Framework.query.get(int(framework_id))
    if not framework:
        flash('Invalid framework selected.', 'error')
        return redirect(url_for('audits.audits'))

    audit = Audit(
        name=name,
        framework=framework.name,
        auditor=request.form.get('auditor', ''),
        status='Scheduled',
        start_date=request.form.get('start_date', ''),
        end_date=request.form.get('end_date', ''),
    )
    db.session.add(audit)
    db.session.flush()

    for control in framework.controls:
        db.session.add(AuditEvidence(audit_id=audit.id, control_id=control.id, status='Missing'))

    db.session.commit()
    flash(f'Audit "{name}" created with {framework.total_controls} evidence items.', 'success')
    return redirect(url_for('audits.audits'))


@audits_bp.route('/audits/<int:audit_id>/evidence/<int:evidence_id>/toggle', methods=['POST'])
@login_required
def toggle_evidence(audit_id, evidence_id):
    evidence = AuditEvidence.query.filter_by(id=evidence_id, audit_id=audit_id).first_or_404()
    if evidence.status == 'Collected':
        evidence.status = 'Missing'
        evidence.collected_at = None
    else:
        evidence.status = 'Collected'
        evidence.collected_at = datetime.utcnow()

    db.session.commit()
    flash(f'Evidence for {evidence.control.code} marked as {evidence.status}.', 'success')
    return redirect(url_for('audits.audits'))


@audits_bp.route('/audits/<int:audit_id>/delete', methods=['POST'])
@login_required
def delete_audit(audit_id):
    audit = Audit.query.get_or_404(audit_id)
    name = audit.name
    db.session.delete(audit)
    db.session.commit()
    flash(f'Audit "{name}" deleted.', 'info')
    return redirect(url_for('audits.audits'))
