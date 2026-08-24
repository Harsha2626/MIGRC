import os
import re
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, Framework, Control, Evidence, EvidenceMapping, ComplianceSnapshot
from app.services.activity import log_activity
from app.services.notifications import notify_evidence_rejected
from app.services.pdf_reports import build_compliance_report_pdf, build_soc2_readiness_pdf
from app.utils import allowed_file, require_permission

compliance_bp = Blueprint('compliance', __name__)


def _code_sort_key(code):
    """Natural sort so '4.1' < '4.2' < ... < '10.2' < 'A.5.1' < ... < 'A.5.10' < 'A.5.11'."""
    return [int(part) if part.isdigit() else part for part in re.split(r'(\d+)', code or '')]


@compliance_bp.route('/compliance')
@login_required
def compliance():
    frameworks = Framework.query.all()
    return render_template('compliance.html', page='compliance',
        frameworks=[fw.to_dict() for fw in frameworks])


@compliance_bp.route('/compliance/add', methods=['POST'])
@login_required
@require_permission('write')
def add_framework():
    name = request.form.get('name', '').strip()
    if name == '__custom__':
        name = request.form.get('custom_name', '').strip()

    if not name:
        flash('Please select or name a framework.', 'error')
        return redirect(url_for('compliance.compliance'))

    if Framework.query.filter_by(name=name).first():
        flash(f'A framework named "{name}" already exists.', 'error')
        return redirect(url_for('compliance.compliance'))

    category = request.form.get('category', 'Security')
    owner = request.form.get('owner', '').strip()
    target_date = request.form.get('target_date')

    fw = Framework(
        name=name,
        category=category,
        owner=owner,
        status='Not Started',
        icon='shield-halved',
        target_date=datetime.strptime(target_date, '%Y-%m-%d').date() if target_date else None,
    )
    db.session.add(fw)
    log_activity('created', 'Framework', name)
    db.session.commit()

    flash(f'Framework "{name}" added. It has no controls yet — controls are currently seeded, not added from the UI.', 'success')
    return redirect(url_for('compliance.compliance'))


@compliance_bp.route('/compliance/<int:framework_id>')
@login_required
def framework_detail(framework_id):
    fw = Framework.query.get_or_404(framework_id)
    controls = Control.query.filter_by(framework_id=fw.id).all()
    controls.sort(key=lambda c: _code_sort_key(c.code))

    # Group controls by category
    categories = {}
    for c in controls:
        cat = c.category or 'Uncategorized'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(c)

    # Build evidence count per control for badges
    evidence_counts = {}
    for c in controls:
        evidence_counts[c.id] = c.evidence_mappings.count()

    return render_template('compliance_detail.html', page='compliance',
        framework=fw, controls=controls, categories=categories,
        evidence_counts=evidence_counts)


@compliance_bp.route('/compliance/<int:framework_id>/control/<int:control_id>')
@login_required
def control_detail(framework_id, control_id):
    fw = Framework.query.get_or_404(framework_id)
    ctrl = Control.query.get_or_404(control_id)

    # Get all evidence mapped to this control
    mappings = EvidenceMapping.query.filter_by(control_id=ctrl.id).all()
    evidence_list = []
    for m in mappings:
        ev = m.evidence
        evidence_list.append({
            'id': ev.id,
            'title': ev.title,
            'description': ev.description,
            'file_name': ev.file_name,
            'file_type': ev.file_type,
            'file_size': ev.file_size,
            'source_type': ev.source_type,
            'uploaded_by': ev.uploaded_by.name if ev.uploaded_by else '—',
            'status': ev.status,
            'review_notes': ev.review_notes,
            'created_at': ev.created_at,
            'audit_period_start': ev.audit_period_start,
            'audit_period_end': ev.audit_period_end,
            'mapping_id': m.id,
        })

    # Get all controls in this framework for multi-map dropdown
    all_controls = Control.query.filter_by(framework_id=fw.id).all()
    all_controls.sort(key=lambda c: _code_sort_key(c.code))

    return render_template('control_detail.html', page='compliance',
        framework=fw, control=ctrl, evidence_list=evidence_list,
        all_controls=all_controls)


# ---- EVIDENCE UPLOAD ----
@compliance_bp.route('/compliance/<int:framework_id>/control/<int:control_id>/upload', methods=['POST'])
@login_required
@require_permission('write')
def upload_evidence(framework_id, control_id):
    fw = Framework.query.get_or_404(framework_id)
    ctrl = Control.query.get_or_404(control_id)

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    source_type = request.form.get('source_type', 'Manual Upload')
    audit_start = request.form.get('audit_period_start')
    audit_end = request.form.get('audit_period_end')
    map_control_ids = request.form.getlist('map_controls')

    file = request.files.get('file')

    if not title:
        flash('Evidence title is required.', 'error')
        return redirect(url_for('compliance.control_detail', framework_id=fw.id, control_id=ctrl.id))

    if not file or file.filename == '':
        flash('Please select a file to upload.', 'error')
        return redirect(url_for('compliance.control_detail', framework_id=fw.id, control_id=ctrl.id))

    if not allowed_file(file.filename):
        flash('File type not allowed. Use: pdf, png, jpg, csv, xlsx, doc, docx', 'error')
        return redirect(url_for('compliance.control_detail', framework_id=fw.id, control_id=ctrl.id))

    # Save file
    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)

    # Get file size
    file_size = os.path.getsize(file_path)
    file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    # Create Evidence record
    evidence = Evidence(
        title=title,
        description=description,
        file_path=unique_filename,
        file_name=filename,
        file_type=file_type,
        file_size=file_size,
        source_type=source_type,
        uploaded_by_id=current_user.id,
        audit_period_start=datetime.strptime(audit_start, '%Y-%m-%d').date() if audit_start else None,
        audit_period_end=datetime.strptime(audit_end, '%Y-%m-%d').date() if audit_end else None,
    )
    db.session.add(evidence)
    db.session.flush()

    # Map to current control
    mapped_ids = set()
    mapped_ids.add(ctrl.id)
    db.session.add(EvidenceMapping(evidence_id=evidence.id, control_id=ctrl.id))

    # Map to additional controls if selected
    for cid in map_control_ids:
        try:
            cid_int = int(cid)
            if cid_int not in mapped_ids:
                mapped_ids.add(cid_int)
                db.session.add(EvidenceMapping(evidence_id=evidence.id, control_id=cid_int))
        except ValueError:
            pass

    db.session.commit()

    # Auto-update control status for all mapped controls
    for cid in mapped_ids:
        _recalculate_control_status(cid)

    # Take compliance snapshot for affected frameworks
    affected_fw_ids = set()
    affected_fw_ids.add(fw.id)
    for cid in mapped_ids:
        c = Control.query.get(cid)
        if c:
            affected_fw_ids.add(c.framework_id)
    for fid in affected_fw_ids:
        _take_compliance_snapshot(fid)

    log_activity('uploaded', 'Evidence', title,
        f'{current_user.name} uploaded evidence "{title}" and mapped it to {len(mapped_ids)} control(s)')
    db.session.commit()

    flash(f'Evidence "{title}" uploaded and mapped to {len(mapped_ids)} control(s).', 'success')
    return redirect(url_for('compliance.control_detail', framework_id=fw.id, control_id=ctrl.id))


# ---- EVIDENCE REVIEW (Approve / Reject) ----
@compliance_bp.route('/evidence/<int:evidence_id>/review', methods=['POST'])
@login_required
@require_permission('review_evidence')
def review_evidence(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)
    action = request.form.get('action')
    review_notes = request.form.get('review_notes', '').strip()

    if action == 'approve':
        evidence.status = 'Approved'
        flash(f'Evidence "{evidence.title}" approved.', 'success')
    elif action == 'reject':
        evidence.status = 'Rejected'
        flash(f'Evidence "{evidence.title}" rejected.', 'error')
    else:
        flash('Invalid action.', 'error')
        return redirect(request.referrer or '/')

    evidence.review_notes = review_notes
    evidence.reviewed_by = current_user.name
    evidence.reviewed_at = datetime.utcnow()

    # Recalculate status for all controls mapped to this evidence
    affected_fw_ids = set()
    for mapping in evidence.evidence_mappings:
        _recalculate_control_status(mapping.control_id)
        ctrl = Control.query.get(mapping.control_id)
        if ctrl:
            affected_fw_ids.add(ctrl.framework_id)

    # Take compliance snapshot for affected frameworks
    for fid in affected_fw_ids:
        _take_compliance_snapshot(fid)

    log_activity('approved' if action == 'approve' else 'rejected', 'Evidence', evidence.title)
    db.session.commit()

    if action == 'reject':
        notify_evidence_rejected(evidence)

    return redirect(request.referrer or '/')


# ---- EVIDENCE DELETE ----
@compliance_bp.route('/evidence/<int:evidence_id>/delete', methods=['POST'])
@login_required
@require_permission('delete')
def delete_evidence(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)
    affected_control_ids = [m.control_id for m in evidence.evidence_mappings]

    # Delete the file from disk
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, evidence.file_path) if evidence.file_path else None
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    title = evidence.title
    db.session.delete(evidence)
    log_activity('deleted', 'Evidence', title)
    db.session.commit()

    # Recalculate status for affected controls
    affected_fw_ids = set()
    for cid in affected_control_ids:
        _recalculate_control_status(cid)
        ctrl = Control.query.get(cid)
        if ctrl:
            affected_fw_ids.add(ctrl.framework_id)

    # Take compliance snapshot for affected frameworks
    for fid in affected_fw_ids:
        _take_compliance_snapshot(fid)

    db.session.commit()

    flash(f'Evidence "{title}" deleted.', 'success')
    return redirect(request.referrer or '/')


def _recalculate_control_status(control_id):
    """Recalculate a control's status based on its mapped evidence."""
    ctrl = Control.query.get(control_id)
    if not ctrl:
        return

    mappings = EvidenceMapping.query.filter_by(control_id=control_id).all()
    if not mappings:
        ctrl.status = 'Not Assessed'
        return

    statuses = [m.evidence.status for m in mappings]

    # If any evidence is approved and none are rejected → Passing
    # If any evidence is rejected → Failing
    # Otherwise (all pending) → Not Assessed
    has_approved = 'Approved' in statuses
    has_rejected = 'Rejected' in statuses

    if has_rejected:
        ctrl.status = 'Failing'
    elif has_approved:
        ctrl.status = 'Passing'
    else:
        ctrl.status = 'Not Assessed'


def _take_compliance_snapshot(framework_id):
    """Create or update today's compliance snapshot for a framework."""
    fw = Framework.query.get(framework_id)
    if not fw:
        return

    today = date.today()

    # Upsert: update today's snapshot if it exists, otherwise create new
    snapshot = ComplianceSnapshot.query.filter_by(
        framework_id=fw.id, snapshot_date=today
    ).first()

    if not snapshot:
        snapshot = ComplianceSnapshot(framework_id=fw.id, snapshot_date=today)
        db.session.add(snapshot)

    snapshot.score = fw.compliance_score
    snapshot.passing = fw.passing
    snapshot.failing = fw.failing
    snapshot.not_assessed = fw.not_assessed
    snapshot.not_applicable = fw.not_applicable
    snapshot.total_controls = fw.total_controls


@compliance_bp.route('/compliance/<int:framework_id>/report.pdf')
@login_required
def framework_report_pdf(framework_id):
    fw = Framework.query.get_or_404(framework_id)
    pdf_bytes = build_compliance_report_pdf(fw)
    filename = f"{fw.name.replace(' ', '_')}_compliance_report.pdf"
    return Response(pdf_bytes, mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename={filename}'})
