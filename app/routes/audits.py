import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, Audit, AuditEvidence, AuditFinding, Remediation, Framework, Control, Evidence, EvidenceMapping
from app.services.activity import log_activity
from app.utils import allowed_file

audits_bp = Blueprint('audits', __name__)

FINDING_TYPES = ['Observation', 'Non-Conformity', 'Recommendation']
FINDING_SEVERITIES = ['Low', 'Medium', 'High', 'Critical']


@audits_bp.route('/audits')
@login_required
def audits():
    all_audits = Audit.query.all()
    frameworks = Framework.query.order_by(Framework.name).all()
    all_controls = Control.query.order_by(Control.code).all()
    return render_template('audits.html', page='audits', audits=all_audits,
        frameworks=frameworks, all_controls=all_controls)


@audits_bp.route('/audits/add', methods=['POST'])
@login_required
def add_audit():
    name = request.form.get('name', '').strip()
    framework_id = request.form.get('framework_id')
    control_ids = request.form.getlist('control_ids')

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

    scope_controls = (
        [Control.query.get(int(cid)) for cid in control_ids] if control_ids
        else list(framework.controls)
    )
    for control in scope_controls:
        if control:
            db.session.add(AuditEvidence(audit_id=audit.id, control_id=control.id, status='Missing'))

    log_activity('created', 'Audit', name, f'{current_user.name} created audit "{name}" scoped to {len(scope_controls)} control(s)')
    db.session.commit()
    flash(f'Audit "{name}" created with {len(scope_controls)} control(s) in scope.', 'success')
    return redirect(url_for('audits.audit_detail', audit_id=audit.id))


@audits_bp.route('/audits/<int:audit_id>')
@login_required
def audit_detail(audit_id):
    audit = Audit.query.get_or_404(audit_id)
    evidence_items = audit.evidence_items.order_by(AuditEvidence.id).all()

    # For each in-scope control, find already-uploaded Evidence mapped to it (for the "link existing" dropdown)
    existing_evidence_by_control = {}
    for item in evidence_items:
        mappings = EvidenceMapping.query.filter_by(control_id=item.control_id).all()
        existing_evidence_by_control[item.control_id] = [m.evidence for m in mappings]

    findings = audit.finding_items.order_by(AuditFinding.created_at.desc()).all()
    all_controls = Control.query.order_by(Control.code).all()

    return render_template('audit_detail.html', page='audits',
        audit=audit, evidence_items=evidence_items,
        existing_evidence_by_control=existing_evidence_by_control,
        findings=findings, all_controls=all_controls,
        finding_types=FINDING_TYPES, finding_severities=FINDING_SEVERITIES)


@audits_bp.route('/audits/<int:audit_id>/status', methods=['POST'])
@login_required
def update_audit_status(audit_id):
    audit = Audit.query.get_or_404(audit_id)
    target = request.form.get('status')

    if target != audit.next_status:
        flash('Invalid status transition.', 'error')
        return redirect(url_for('audits.audit_detail', audit_id=audit.id))

    audit.status = target
    log_activity('status_changed', 'Audit', audit.name, f'{current_user.name} moved audit "{audit.name}" to {target}')
    db.session.commit()
    flash(f'Audit moved to {target}.', 'success')
    return redirect(url_for('audits.audit_detail', audit_id=audit.id))


@audits_bp.route('/audits/<int:audit_id>/evidence/<int:evidence_id>/toggle', methods=['POST'])
@login_required
def toggle_evidence(audit_id, evidence_id):
    evidence = AuditEvidence.query.filter_by(id=evidence_id, audit_id=audit_id).first_or_404()
    if evidence.status == 'Collected':
        evidence.status = 'Missing'
        evidence.collected_at = None
        evidence.evidence_id = None
    else:
        evidence.status = 'Collected'
        evidence.collected_at = datetime.utcnow()

    log_activity('status_changed', 'Audit', evidence.audit.name,
        f'Evidence for {evidence.control.code} marked as {evidence.status} on audit "{evidence.audit.name}"')
    db.session.commit()
    flash(f'Evidence for {evidence.control.code} marked as {evidence.status}.', 'success')
    return redirect(url_for('audits.audit_detail', audit_id=audit_id))


@audits_bp.route('/audits/<int:audit_id>/evidence/<int:evidence_id>/link', methods=['POST'])
@login_required
def link_evidence(audit_id, evidence_id):
    audit_evidence = AuditEvidence.query.filter_by(id=evidence_id, audit_id=audit_id).first_or_404()
    source_evidence_id = request.form.get('evidence_id')

    evidence = Evidence.query.get(int(source_evidence_id)) if source_evidence_id else None
    if not evidence:
        flash('Please select an evidence file to link.', 'error')
        return redirect(url_for('audits.audit_detail', audit_id=audit_id))

    audit_evidence.evidence_id = evidence.id
    audit_evidence.status = 'Collected'
    audit_evidence.collected_at = datetime.utcnow()

    log_activity('status_changed', 'Audit', audit_evidence.audit.name,
        f'{current_user.name} linked evidence "{evidence.title}" to {audit_evidence.control.code} on audit "{audit_evidence.audit.name}"')
    db.session.commit()
    flash(f'Linked "{evidence.title}" to {audit_evidence.control.code}.', 'success')
    return redirect(url_for('audits.audit_detail', audit_id=audit_id))


@audits_bp.route('/audits/<int:audit_id>/evidence/<int:evidence_id>/upload', methods=['POST'])
@login_required
def upload_audit_evidence(audit_id, evidence_id):
    audit_evidence = AuditEvidence.query.filter_by(id=evidence_id, audit_id=audit_id).first_or_404()
    file = request.files.get('file')
    title = request.form.get('title', '').strip() or f'Evidence for {audit_evidence.control.code}'

    if not file or file.filename == '':
        flash('Please select a file to upload.', 'error')
        return redirect(url_for('audits.audit_detail', audit_id=audit_id))

    if not allowed_file(file.filename):
        flash('File type not allowed. Use: pdf, png, jpg, csv, xlsx, doc, docx', 'error')
        return redirect(url_for('audits.audit_detail', audit_id=audit_id))

    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    unique_filename = f'{timestamp}_{filename}'
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)

    evidence = Evidence(
        title=title,
        file_path=unique_filename,
        file_name=filename,
        file_type=filename.rsplit('.', 1)[1].lower() if '.' in filename else '',
        file_size=os.path.getsize(file_path),
        source_type='Manual Upload',
        uploaded_by_id=current_user.id,
        status='Approved',
    )
    db.session.add(evidence)
    db.session.flush()

    db.session.add(EvidenceMapping(evidence_id=evidence.id, control_id=audit_evidence.control_id))
    audit_evidence.evidence_id = evidence.id
    audit_evidence.status = 'Collected'
    audit_evidence.collected_at = datetime.utcnow()

    log_activity('uploaded', 'Evidence', title,
        f'{current_user.name} uploaded "{title}" for {audit_evidence.control.code} on audit "{audit_evidence.audit.name}"')
    db.session.commit()
    flash(f'Evidence uploaded for {audit_evidence.control.code}.', 'success')
    return redirect(url_for('audits.audit_detail', audit_id=audit_id))


@audits_bp.route('/audits/<int:audit_id>/findings/add', methods=['POST'])
@login_required
def add_finding(audit_id):
    audit = Audit.query.get_or_404(audit_id)
    description = request.form.get('description', '').strip()
    if not description:
        flash('Finding description is required.', 'error')
        return redirect(url_for('audits.audit_detail', audit_id=audit_id))

    control_id = request.form.get('control_id')
    finding = AuditFinding(
        audit_id=audit.id,
        control_id=int(control_id) if control_id else None,
        type=request.form.get('type', 'Observation'),
        severity=request.form.get('severity', 'Medium'),
        description=description,
        status='Open',
    )
    db.session.add(finding)
    log_activity('created', 'Audit', audit.name, f'{current_user.name} logged a finding on audit "{audit.name}": {description[:80]}')
    db.session.commit()
    flash('Finding logged.', 'success')
    return redirect(url_for('audits.audit_detail', audit_id=audit_id))


@audits_bp.route('/audits/<int:audit_id>/findings/<int:finding_id>/remediation', methods=['POST'])
@login_required
def save_remediation(audit_id, finding_id):
    finding = AuditFinding.query.filter_by(id=finding_id, audit_id=audit_id).first_or_404()
    status = request.form.get('status', 'Planned')

    if finding.remediation:
        remediation = finding.remediation
    else:
        remediation = Remediation(finding_id=finding.id)
        db.session.add(remediation)

    remediation.owner = request.form.get('owner', '')
    remediation.deadline = request.form.get('deadline', '')
    remediation.status = status
    remediation.notes = request.form.get('notes', '')
    if status == 'Completed':
        remediation.completed_at = datetime.utcnow()
        finding.status = 'Remediated'
    else:
        finding.status = 'Open'

    log_activity('status_changed', 'Audit', finding.audit.name,
        f'{current_user.name} set remediation for a finding on audit "{finding.audit.name}" to {status}')
    db.session.commit()
    flash('Remediation updated.', 'success')
    return redirect(url_for('audits.audit_detail', audit_id=audit_id))


@audits_bp.route('/audits/<int:audit_id>/report')
@login_required
def audit_report(audit_id):
    audit = Audit.query.get_or_404(audit_id)
    evidence_items = audit.evidence_items.order_by(AuditEvidence.id).all()
    findings = audit.finding_items.order_by(AuditFinding.created_at).all()
    return render_template('audit_report.html', audit=audit, evidence_items=evidence_items, findings=findings)


@audits_bp.route('/audits/<int:audit_id>/delete', methods=['POST'])
@login_required
def delete_audit(audit_id):
    audit = Audit.query.get_or_404(audit_id)
    name = audit.name
    db.session.delete(audit)
    log_activity('deleted', 'Audit', name)
    db.session.commit()
    flash(f'Audit "{name}" deleted.', 'info')
    return redirect(url_for('audits.audits'))
