import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import (
    db, Vendor, VENDOR_REASSESSMENT_DAYS, QuestionnaireTemplate, QuestionnaireQuestion,
    VendorAssessment, VendorAssessmentResponse, VendorRiskSnapshot, Evidence,
)
from app.services.activity import log_activity
from app.services.csv_export import csv_response
from app.utils import allowed_file, parse_date_safe

vendors_bp = Blueprint('vendors', __name__)

RISK_TIER_MIDPOINTS = {'Critical': 90, 'High': 70, 'Medium': 50, 'Low': 20}


def _next_assessment_date(risk_tier, from_date=None):
    from_date = from_date or datetime.utcnow().date()
    days = VENDOR_REASSESSMENT_DAYS.get(risk_tier, 180)
    return (from_date + timedelta(days=days)).strftime('%Y-%m-%d')


@vendors_bp.route('/vendors')
@login_required
def vendors():
    all_vendors = Vendor.query.all()
    return render_template('vendors.html', page='vendors', vendors=all_vendors,
        vendor_dicts=[v.to_dict() for v in all_vendors])


@vendors_bp.route('/vendors/add', methods=['POST'])
@login_required
def add_vendor():
    name = request.form.get('name', '').strip()
    risk_tier = request.form.get('risk_tier', 'Medium')

    if not name:
        flash('Vendor name is required.', 'error')
        return redirect(url_for('vendors.vendors'))

    if risk_tier not in RISK_TIER_MIDPOINTS:
        risk_tier = 'Medium'

    today = datetime.utcnow().date()
    vendor = Vendor(
        name=name,
        category=request.form.get('category', ''),
        risk_tier=risk_tier,
        risk_score=RISK_TIER_MIDPOINTS[risk_tier],
        status='Under Review',
        contact_name=request.form.get('contact_name', ''),
        contact_email=request.form.get('contact_email', ''),
        last_assessment=today.strftime('%Y-%m-%d'),
        next_assessment=_next_assessment_date(risk_tier, today),
        compliance=request.form.getlist('compliance'),
    )
    db.session.add(vendor)
    log_activity('created', 'Vendor', name)
    db.session.commit()

    flash(f'Vendor "{name}" added.', 'success')
    return redirect(url_for('vendors.vendors'))


@vendors_bp.route('/vendors/<int:vendor_id>')
@login_required
def vendor_detail(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    assessments = vendor.assessments.order_by(VendorAssessment.id.desc()).all()
    documents = vendor.documents.all()
    templates = QuestionnaireTemplate.query.order_by(QuestionnaireTemplate.name).all()

    snapshots = vendor.risk_snapshots.order_by(VendorRiskSnapshot.snapshot_date).all()
    trend_labels = [s.snapshot_date.strftime('%d %b') for s in snapshots]
    trend_data = [s.risk_score for s in snapshots]

    return render_template('vendor_detail.html', page='vendors',
        vendor=vendor, assessments=assessments, documents=documents, templates=templates,
        trend_labels=trend_labels, trend_data=trend_data)


@vendors_bp.route('/vendors/<int:vendor_id>/edit', methods=['POST'])
@login_required
def edit_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    name = request.form.get('name', '').strip()
    risk_tier = request.form.get('risk_tier', vendor.risk_tier)

    if not name:
        flash('Vendor name is required.', 'error')
        return redirect(url_for('vendors.vendors'))

    if risk_tier not in RISK_TIER_MIDPOINTS:
        risk_tier = vendor.risk_tier

    tier_changed = risk_tier != vendor.risk_tier
    vendor.name = name
    vendor.category = request.form.get('category', vendor.category)
    vendor.risk_tier = risk_tier
    vendor.risk_score = RISK_TIER_MIDPOINTS[risk_tier]
    vendor.status = request.form.get('status', vendor.status)
    vendor.contact_name = request.form.get('contact_name', vendor.contact_name)
    vendor.contact_email = request.form.get('contact_email', vendor.contact_email)
    vendor.compliance = request.form.getlist('compliance') or vendor.compliance

    if tier_changed:
        last = parse_date_safe(vendor.last_assessment) or datetime.utcnow().date()
        vendor.next_assessment = _next_assessment_date(risk_tier, last)

    log_activity('updated', 'Vendor', name)
    db.session.commit()
    flash(f'Vendor "{name}" updated.', 'success')
    return redirect(url_for('vendors.vendors'))


@vendors_bp.route('/vendors/<int:vendor_id>/delete', methods=['POST'])
@login_required
def delete_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    name = vendor.name
    db.session.delete(vendor)
    log_activity('deleted', 'Vendor', name)
    db.session.commit()
    flash(f'Vendor "{name}" deleted.', 'info')
    return redirect(url_for('vendors.vendors'))


@vendors_bp.route('/vendors/export')
@login_required
def export_vendors():
    rows = [(v.name, v.category, v.risk_tier, v.risk_score, v.status, v.contact_name, v.contact_email, v.last_assessment, v.next_assessment) for v in Vendor.query.all()]
    return csv_response('vendors.csv', ['Name', 'Category', 'Risk Tier', 'Risk Score', 'Status', 'Contact Name', 'Contact Email', 'Last Assessment', 'Next Assessment'], rows)


# ---- QUESTIONNAIRE TEMPLATES ----

@vendors_bp.route('/vendors/questionnaires')
@login_required
def questionnaires():
    templates = QuestionnaireTemplate.query.order_by(QuestionnaireTemplate.name).all()
    return render_template('questionnaire_templates.html', page='vendors', templates=templates)


@vendors_bp.route('/vendors/questionnaires/add', methods=['POST'])
@login_required
def add_questionnaire():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Template name is required.', 'error')
        return redirect(url_for('vendors.questionnaires'))

    template = QuestionnaireTemplate(name=name, description=request.form.get('description', ''))
    db.session.add(template)
    db.session.flush()

    questions = [q.strip() for q in request.form.get('questions', '').splitlines() if q.strip()]
    for i, q in enumerate(questions):
        db.session.add(QuestionnaireQuestion(template_id=template.id, question_text=q, order=i))

    log_activity('created', 'Vendor', name, f'{current_user.name} created questionnaire template "{name}" with {len(questions)} question(s)')
    db.session.commit()
    flash(f'Questionnaire "{name}" created with {len(questions)} question(s).', 'success')
    return redirect(url_for('vendors.questionnaires'))


@vendors_bp.route('/vendors/questionnaires/<int:template_id>/delete', methods=['POST'])
@login_required
def delete_questionnaire(template_id):
    template = QuestionnaireTemplate.query.get_or_404(template_id)
    name = template.name
    db.session.delete(template)
    log_activity('deleted', 'Vendor', name, f'{current_user.name} deleted questionnaire template "{name}"')
    db.session.commit()
    flash(f'Questionnaire "{name}" deleted.', 'info')
    return redirect(url_for('vendors.questionnaires'))


# ---- VENDOR ASSESSMENTS ----

@vendors_bp.route('/vendors/<int:vendor_id>/assessments/send', methods=['POST'])
@login_required
def send_assessment(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    template_id = request.form.get('template_id')
    template = QuestionnaireTemplate.query.get(int(template_id)) if template_id else None

    if not template:
        flash('Please select a questionnaire template.', 'error')
        return redirect(url_for('vendors.vendor_detail', vendor_id=vendor_id))

    assessment = VendorAssessment(
        vendor_id=vendor.id, template_id=template.id, status='Sent',
        sent_date=datetime.utcnow().strftime('%Y-%m-%d'),
    )
    db.session.add(assessment)
    log_activity('created', 'Vendor', vendor.name, f'{current_user.name} sent "{template.name}" assessment to {vendor.name}')
    db.session.commit()
    flash(f'Assessment sent to {vendor.name}.', 'success')
    return redirect(url_for('vendors.vendor_detail', vendor_id=vendor_id))


@vendors_bp.route('/vendors/<int:vendor_id>/assessments/<int:assessment_id>')
@login_required
def assessment_detail(vendor_id, assessment_id):
    assessment = VendorAssessment.query.filter_by(id=assessment_id, vendor_id=vendor_id).first_or_404()
    existing = {r.question_id: r.answer_text for r in assessment.responses}
    return render_template('vendor_assessment.html', page='vendors',
        assessment=assessment, existing=existing)


@vendors_bp.route('/vendors/<int:vendor_id>/assessments/<int:assessment_id>/respond', methods=['POST'])
@login_required
def respond_assessment(vendor_id, assessment_id):
    assessment = VendorAssessment.query.filter_by(id=assessment_id, vendor_id=vendor_id).first_or_404()
    vendor = assessment.vendor
    verdict = request.form.get('verdict')
    complete = request.form.get('complete') == '1'

    for question in assessment.template.questions:
        answer = request.form.get(f'question_{question.id}', '').strip()
        response = VendorAssessmentResponse.query.filter_by(assessment_id=assessment.id, question_id=question.id).first()
        if response:
            response.answer_text = answer
        else:
            db.session.add(VendorAssessmentResponse(assessment_id=assessment.id, question_id=question.id, answer_text=answer))

    assessment.reviewer_notes = request.form.get('reviewer_notes', '')

    if complete:
        assessment.status = 'Completed'
        assessment.verdict = verdict
        assessment.completed_date = datetime.utcnow().strftime('%Y-%m-%d')
        vendor.last_assessment = assessment.completed_date
        vendor.next_assessment = _next_assessment_date(vendor.risk_tier)
        log_activity('status_changed', 'Vendor', vendor.name,
            f'{current_user.name} completed the assessment for {vendor.name} ({verdict})')
    else:
        assessment.status = 'In Progress'
        log_activity('updated', 'Vendor', vendor.name, f'{current_user.name} saved progress on {vendor.name}\'s assessment')

    db.session.commit()
    flash('Assessment saved.' if not complete else f'Assessment completed with verdict: {verdict}.', 'success')
    return redirect(url_for('vendors.vendor_detail', vendor_id=vendor_id))


# ---- VENDOR DOCUMENTS (reuses Evidence) ----

@vendors_bp.route('/vendors/<int:vendor_id>/documents/upload', methods=['POST'])
@login_required
def upload_vendor_document(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    file = request.files.get('file')
    title = request.form.get('title', '').strip() or f'Document for {vendor.name}'

    if not file or file.filename == '':
        flash('Please select a file to upload.', 'error')
        return redirect(url_for('vendors.vendor_detail', vendor_id=vendor_id))

    if not allowed_file(file.filename):
        flash('File type not allowed. Use: pdf, png, jpg, csv, xlsx, doc, docx', 'error')
        return redirect(url_for('vendors.vendor_detail', vendor_id=vendor_id))

    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    unique_filename = f'{timestamp}_{filename}'
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)

    doc = Evidence(
        title=title,
        file_path=unique_filename,
        file_name=filename,
        file_type=filename.rsplit('.', 1)[1].lower() if '.' in filename else '',
        file_size=os.path.getsize(file_path),
        source_type='Vendor Document',
        uploaded_by_id=current_user.id,
        vendor_id=vendor.id,
        status='Approved',
    )
    db.session.add(doc)
    log_activity('uploaded', 'Vendor', vendor.name, f'{current_user.name} uploaded "{title}" for vendor {vendor.name}')
    db.session.commit()
    flash(f'Document "{title}" uploaded.', 'success')
    return redirect(url_for('vendors.vendor_detail', vendor_id=vendor_id))


@vendors_bp.route('/vendors/<int:vendor_id>/documents/<int:evidence_id>/delete', methods=['POST'])
@login_required
def delete_vendor_document(vendor_id, evidence_id):
    doc = Evidence.query.filter_by(id=evidence_id, vendor_id=vendor_id).first_or_404()
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], doc.file_path) if doc.file_path else None
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    title = doc.title
    vendor = doc.vendor
    db.session.delete(doc)
    log_activity('deleted', 'Vendor', vendor.name if vendor else '', f'{current_user.name} deleted document "{title}"')
    db.session.commit()
    flash(f'Document "{title}" deleted.', 'info')
    return redirect(url_for('vendors.vendor_detail', vendor_id=vendor_id))
