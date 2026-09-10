import os
import re
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response, g
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from app.models import db, Framework, Control, ControlStatus, Evidence, EvidenceMapping, ComplianceSnapshot, Policy
from app.services.activity import log_activity
from app.services.notifications import notify_evidence_rejected
from app.services.pdf_reports import build_compliance_report_pdf, build_soc2_readiness_pdf
from app.services.ai_evidence_review import review_evidence as ai_review_evidence
from app.utils import allowed_file, require_permission

compliance_bp = Blueprint('compliance', __name__)


def _code_sort_key(code):
    """Natural sort so '4.1' < '4.2' < ... < '10.2' < 'A.5.1' < ... < 'A.5.10' < 'A.5.11'."""
    return [int(part) if part.isdigit() else part for part in re.split(r'(\d+)', code or '')]


@compliance_bp.route('/compliance')
@login_required
def compliance():
    if not g.current_org:
        flash('No active organization.', 'error')
        return redirect(url_for('main.dashboard'))
    # Shared library frameworks + whatever this org added privately for itself.
    frameworks = Framework.visible_to(g.current_org.id).order_by(Framework.name).all()
    return render_template('compliance.html', page='compliance',
        frameworks=[dict(fw.to_dict(), is_shared=fw.is_shared) for fw in frameworks])


@compliance_bp.route('/tests')
@login_required
def tests():
    """A unified checklist of every ongoing compliance check: control
    assessments and policy publication status, in one filterable list."""
    if not g.current_org:
        flash('No active organization.', 'error')
        return redirect(url_for('main.dashboard'))
    org_id = g.current_org.id
    rows = []

    # Controls belong to frameworks visible to this org (shared library + their own private ones);
    # each org's status for a control comes from its own ControlStatus row.
    visible_fw_ids = {fw.id for fw in Framework.visible_to(org_id).all()}
    for c in Control.query.filter(Control.framework_id.in_(visible_fw_ids)).all():
        status = c.org_status
        if status == 'Passing':
            display_status = 'Passing'
        elif status == 'Not Applicable':
            display_status = 'Ignored'
        else:  # Failing, Not Assessed
            display_status = 'Fix Required'
        rows.append({
            'name': c.title, 'type': 'Control', 'status': display_status,
            'assignee': c.org_owner or None,
            'framework': c.framework.name if c.framework else None,
            'link': url_for('compliance.control_detail', framework_id=c.framework_id, control_id=c.id),
        })

    for p in Policy.query.filter_by(organization_id=org_id).all():
        if p.status in ('Approved', 'Published'):
            display_status = 'Passing'
        elif p.status == 'Retired':
            display_status = 'Ignored'
        else:  # Not Uploaded, Draft, Needs Review, Pending Approval
            display_status = 'Fix Required'
        rows.append({
            'name': p.name, 'type': 'Policy', 'status': display_status,
            'assignee': p.assigned_reviewer.name if p.assigned_reviewer else None,
            'framework': p.framework or None, 'effort': p.effort_estimate,
            'link': url_for('policies.policy_detail', policy_id=p.id),
        })

    counts = {
        'passing': sum(1 for r in rows if r['status'] == 'Passing'),
        'fix_required': sum(1 for r in rows if r['status'] == 'Fix Required'),
        'ignored': sum(1 for r in rows if r['status'] == 'Ignored'),
    }
    return render_template('tests.html', page='tests', rows=rows, counts=counts)


@compliance_bp.route('/compliance/add', methods=['POST'])
@login_required
@require_permission('write')
def add_framework():
    if not g.current_org:
        flash('No active organization.', 'error')
        return redirect(url_for('main.dashboard'))

    name = request.form.get('name', '').strip()
    if name == '__custom__':
        name = request.form.get('custom_name', '').strip()

    if not name:
        flash('Please select or name a framework.', 'error')
        return redirect(url_for('compliance.compliance'))

    if Framework.visible_to(g.current_org.id).filter_by(name=name).first():
        flash(f'A framework named "{name}" already exists.', 'error')
        return redirect(url_for('compliance.compliance'))

    category = request.form.get('category', 'Security')
    owner = request.form.get('owner', '').strip()
    target_date = request.form.get('target_date')

    # Frameworks added here are private to this org — the shared library (seeded standards
    # like ISO 27001/SOC 2) stays common to everyone and isn't touched by this route.
    fw = Framework(
        organization_id=g.current_org.id,
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


@compliance_bp.route('/compliance/<int:framework_id>/delete', methods=['POST'])
@login_required
@require_permission('delete')
def delete_framework(framework_id):
    if not g.current_org:
        flash('No active organization.', 'error')
        return redirect(url_for('main.dashboard'))

    fw = Framework.visible_to(g.current_org.id).filter_by(id=framework_id).first_or_404()
    name = fw.name

    try:
        db.session.delete(fw)
        log_activity('deleted', 'Framework', name)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f'Can\'t delete "{name}" — one or more of its controls are still referenced by '
              'an existing audit\'s scope. Remove that scope first.', 'error')
        return redirect(url_for('compliance.compliance'))

    flash(f'Framework "{name}" deleted.', 'success')
    return redirect(url_for('compliance.compliance'))


@compliance_bp.route('/compliance/<int:framework_id>')
@login_required
def framework_detail(framework_id):
    fw = Framework.visible_to(g.current_org.id if g.current_org else -1).filter_by(id=framework_id).first_or_404()
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
    fw = Framework.visible_to(g.current_org.id if g.current_org else -1).filter_by(id=framework_id).first_or_404()
    ctrl = Control.query.filter_by(id=control_id, framework_id=fw.id).first_or_404()

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
            'ai_suggested_status': ev.ai_suggested_status,
            'ai_confidence': ev.ai_confidence,
            'ai_rationale': ev.ai_rationale,
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
    if not g.current_org:
        flash('No active organization.', 'error')
        return redirect(url_for('main.dashboard'))
    fw = Framework.visible_to(g.current_org.id).filter_by(id=framework_id).first_or_404()
    ctrl = Control.query.filter_by(id=control_id, framework_id=fw.id).first_or_404()

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
        organization_id=g.current_org.id,
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

    # AI-suggested review (no-op until ANTHROPIC_API_KEY is configured)
    suggestion = ai_review_evidence(evidence, ctrl, upload_folder)
    if suggestion:
        evidence.ai_suggested_status = suggestion.get('status')
        evidence.ai_confidence = suggestion.get('confidence')
        evidence.ai_rationale = suggestion.get('rationale')
        evidence.ai_reviewed_at = datetime.utcnow()

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
    evidence = Evidence.query.filter_by(id=evidence_id, organization_id=g.current_org.id if g.current_org else -1).first_or_404()
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
    evidence = Evidence.query.filter_by(id=evidence_id, organization_id=g.current_org.id if g.current_org else -1).first_or_404()
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
    """Recalculate the current organization's status for a (shared) control, based on that
    org's own mapped evidence — other orgs' evidence on the same control doesn't affect this."""
    org = g.current_org
    if not org:
        return
    ctrl = Control.query.get(control_id)
    if not ctrl:
        return

    mappings = EvidenceMapping.query.filter_by(control_id=control_id).all()
    org_mappings = [m for m in mappings if m.evidence and m.evidence.organization_id == org.id]

    row = ControlStatus.query.filter_by(control_id=control_id, organization_id=org.id).first()
    if not row:
        row = ControlStatus(control_id=control_id, organization_id=org.id)
        db.session.add(row)

    if not org_mappings:
        row.status = 'Not Assessed'
        return

    statuses = [m.evidence.status for m in org_mappings]

    # If any evidence is approved and none are rejected → Passing
    # If any evidence is rejected → Failing
    # Otherwise (all pending) → Not Assessed
    has_approved = 'Approved' in statuses
    has_rejected = 'Rejected' in statuses

    if has_rejected:
        row.status = 'Failing'
    elif has_approved:
        row.status = 'Passing'
    else:
        row.status = 'Not Assessed'


def _take_compliance_snapshot(framework_id):
    """Create or update today's compliance snapshot of the current organization's progress
    against a (shared) framework."""
    org = g.current_org
    if not org:
        return
    fw = Framework.query.get(framework_id)
    if not fw:
        return

    today = date.today()

    # Upsert: update today's snapshot if it exists, otherwise create new
    snapshot = ComplianceSnapshot.query.filter_by(
        organization_id=org.id, framework_id=fw.id, snapshot_date=today
    ).first()

    if not snapshot:
        snapshot = ComplianceSnapshot(organization_id=org.id, framework_id=fw.id, snapshot_date=today)
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
    fw = Framework.visible_to(g.current_org.id if g.current_org else -1).filter_by(id=framework_id).first_or_404()
    pdf_bytes = build_compliance_report_pdf(fw)
    filename = f"{fw.name.replace(' ', '_')}_compliance_report.pdf"
    return Response(pdf_bytes, mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename={filename}'})
