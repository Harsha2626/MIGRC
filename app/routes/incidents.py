from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort
from flask_login import login_required, current_user
from app.models import (db, Incident, IncidentTimelineEntry, Control, Risk, Framework, User,
                        OrganizationMembership, Notification)
from app.services.activity import log_activity
from app.services.csv_export import csv_response
from app.utils import require_permission

incidents_bp = Blueprint('incidents', __name__, url_prefix='/incidents')

SEVERITY_ORDER = {s: i for i, s in enumerate(Incident.SEVERITIES)}


# ---------- helpers (every lookup is org-scoped) ----------

def _org_id():
    return g.current_org.id if g.current_org else -1


def _get_incident(incident_id):
    return Incident.query.filter_by(id=incident_id, organization_id=_org_id()).first_or_404()


def _org_users(org_id):
    return User.query.join(OrganizationMembership, OrganizationMembership.user_id == User.id) \
        .filter(OrganizationMembership.organization_id == org_id, User.is_active_user.is_(True)) \
        .order_by(User.name).all()


def _resolve_owner(raw, org_id):
    """Returns (owner_id, ok). Owner must be an active member of the current org."""
    raw = (raw or '').strip()
    if not raw:
        return None, True
    if not raw.isdigit():
        return None, False
    member = OrganizationMembership.query.filter_by(user_id=int(raw), organization_id=org_id).first()
    return (int(raw), True) if member else (None, False)


def _parse_dt(raw):
    raw = (raw or '').strip()
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _add_entry(incident, entry_type, body):
    entry = IncidentTimelineEntry(incident_id=incident.id, author_id=current_user.id,
                                  entry_type=entry_type, body=body)
    db.session.add(entry)
    return entry


def _notify_owner(incident, title, message):
    if not incident.owner_id or incident.owner_id == current_user.id:
        return
    db.session.add(Notification(
        organization_id=incident.organization_id, user_id=incident.owner_id, type='incident',
        title=title[:200], message=message[:400], link=url_for('incidents.incident_detail', incident_id=incident.id)))


def _visible_controls(org_id):
    fw_ids = [fw.id for fw in Framework.visible_to(org_id).all()]
    if not fw_ids:
        return Control.query.filter(db.false())
    return Control.query.filter(Control.framework_id.in_(fw_ids))


def _filtered_query(org_id):
    q = Incident.query.filter_by(organization_id=org_id)
    search = request.args.get('q', '').strip()
    severity = request.args.get('severity', '')
    status = request.args.get('status', '')
    category = request.args.get('category', '')
    owner = request.args.get('owner', '')
    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(Incident.title.ilike(like), Incident.description.ilike(like),
                            Incident.affected_assets.ilike(like)))
    if severity in Incident.SEVERITIES:
        q = q.filter(Incident.severity == severity)
    if status == 'open':
        q = q.filter(Incident.status != 'Closed')
    elif status in Incident.STATUSES:
        q = q.filter(Incident.status == status)
    if category:
        q = q.filter(Incident.category == category)
    if owner.isdigit():
        q = q.filter(Incident.owner_id == int(owner))
    return q.order_by(Incident.detected_at.desc(), Incident.id.desc())


def _form_values(org_id):
    """Validate shared create/edit fields. Returns (values, error)."""
    f = request.form
    title = f.get('title', '').strip()
    if not title:
        return None, 'Title is required.'
    if len(title) > 200:
        return None, 'Title must be 200 characters or fewer.'
    severity = f.get('severity', 'Medium')
    if severity not in Incident.SEVERITIES:
        return None, 'Invalid severity.'
    detected_at = _parse_dt(f.get('detected_at')) or datetime.utcnow()
    owner_id, ok = _resolve_owner(f.get('owner_id'), org_id)
    if not ok:
        return None, 'Owner must be a member of this organization.'
    category = f.get('category', '').strip()[:50]
    return {
        'title': title, 'severity': severity, 'category': category or None,
        'description': f.get('description', '').strip(), 'detected_at': detected_at,
        'owner_id': owner_id, 'affected_assets': f.get('affected_assets', '').strip(),
        'root_cause': f.get('root_cause', '').strip(),
    }, None


def _form_context(incident=None):
    return dict(page='incidents', incident=incident, users=_org_users(_org_id()),
                severities=Incident.SEVERITIES, categories=Incident.CATEGORIES)


# ---------- list / export ----------

@incidents_bp.route('')
@login_required
def incidents():
    if not g.current_org:
        flash('No active organization.', 'error')
        return redirect(url_for('main.dashboard'))
    org_id = g.current_org.id
    rows = _filtered_query(org_id).all()

    all_inc = Incident.query.filter_by(organization_id=org_id).all()
    open_inc = [i for i in all_inc if i.is_open]
    hours = [i.resolution_hours for i in all_inc if i.resolution_hours is not None]
    mttr = round(sum(hours) / len(hours), 1) if hours else None
    kpis = {
        'total': len(all_inc), 'open': len(open_inc),
        'critical': sum(1 for i in open_inc if i.severity == 'Critical'),
        'mttr_hours': mttr, 'closed': len(hours),
    }
    filters = {k: request.args.get(k, '') for k in ('q', 'severity', 'status', 'category', 'owner')}
    return render_template('incidents.html', page='incidents', incidents=rows, kpis=kpis,
                           filters=filters, export_args={k: v for k, v in filters.items() if v},
                           users=_org_users(org_id), severities=Incident.SEVERITIES,
                           statuses=Incident.STATUSES, categories=Incident.CATEGORIES,
                           )


@incidents_bp.route('/export.csv')
@login_required
def export_csv():
    if not g.current_org:
        abort(404)
    rows = _filtered_query(g.current_org.id).all()
    headers = ['ID', 'Title', 'Severity', 'Status', 'Category', 'Detected At', 'Owner', 'Reported By',
               'Affected Assets', 'Root Cause', 'Resolution Summary', 'Closed At', 'Hours To Resolve']
    data = [[i.id, i.title, i.severity, i.status, i.category or '',
             i.detected_at.strftime('%Y-%m-%d %H:%M') if i.detected_at else '',
             i.owner.name if i.owner else '', i.reported_by.name if i.reported_by else '',
             i.affected_assets or '', i.root_cause or '', i.resolution_summary or '',
             i.closed_at.strftime('%Y-%m-%d %H:%M') if i.closed_at else '',
             f'{i.resolution_hours:.1f}' if i.resolution_hours is not None else ''] for i in rows]
    return csv_response('incidents.csv', headers, data)


# ---------- create / edit ----------

@incidents_bp.route('/new', methods=['GET', 'POST'])
@login_required
@require_permission('write')
def new_incident():
    if not g.current_org:
        flash('No active organization.', 'error')
        return redirect(url_for('main.dashboard'))
    org_id = g.current_org.id
    if request.method == 'POST':
        values, error = _form_values(org_id)
        if error:
            flash(error, 'error')
            return render_template('incident_form.html', **_form_context()), 400
        incident = Incident(organization_id=org_id, status='Detected', reported_by_id=current_user.id, **values)
        db.session.add(incident)
        db.session.flush()
        _add_entry(incident, 'status_change', 'Incident reported with status Detected.')
        log_activity('created', 'Incident', incident.title)
        _notify_owner(incident, f'Incident assigned: {incident.title}',
                      f'{current_user.name} assigned you a {incident.severity} severity incident.')
        db.session.commit()
        flash('Incident reported.', 'success')
        return redirect(url_for('incidents.incident_detail', incident_id=incident.id))
    return render_template('incident_form.html', **_form_context())


@incidents_bp.route('/<int:incident_id>/edit', methods=['GET', 'POST'])
@login_required
@require_permission('write')
def edit_incident(incident_id):
    incident = _get_incident(incident_id)
    if request.method == 'POST':
        values, error = _form_values(incident.organization_id)
        if error:
            flash(error, 'error')
            return render_template('incident_form.html', **_form_context(incident)), 400
        old_owner, old_sev = incident.owner_id, incident.severity
        for k, v in values.items():
            setattr(incident, k, v)
        if incident.severity != old_sev:
            _add_entry(incident, 'action', f'Severity changed from {old_sev} to {incident.severity}.')
        if incident.owner_id != old_owner:
            name = incident.owner.name if incident.owner else 'unassigned'
            _add_entry(incident, 'action', f'Owner changed to {name}.')
            _notify_owner(incident, f'Incident assigned: {incident.title}',
                          f'{current_user.name} assigned you a {incident.severity} severity incident.')
        log_activity('updated', 'Incident', incident.title)
        db.session.commit()
        flash('Incident updated.', 'success')
        return redirect(url_for('incidents.incident_detail', incident_id=incident.id))
    return render_template('incident_form.html', **_form_context(incident))


# ---------- detail ----------

@incidents_bp.route('/<int:incident_id>')
@login_required
def incident_detail(incident_id):
    incident = _get_incident(incident_id)
    org_id = incident.organization_id
    idx = Incident.STATUSES.index(incident.status) if incident.status in Incident.STATUSES else 0
    next_status = Incident.STATUSES[idx + 1] if idx + 1 < len(Incident.STATUSES) else None
    prev_status = Incident.STATUSES[idx - 1] if idx > 0 else None
    linked_control_ids = {c.id for c in incident.controls}
    linked_risk_ids = {r.id for r in incident.risks}
    available_controls = _visible_controls(org_id).filter(~Control.id.in_(linked_control_ids)) \
        .order_by(Control.code).limit(500).all() if can_link() else []
    available_risks = Risk.query.filter_by(organization_id=org_id).filter(~Risk.id.in_(linked_risk_ids)) \
        .order_by(Risk.title).all() if can_link() else []
    hours = incident.resolution_hours
    return render_template('incident_detail.html', page='incidents', incident=incident,
                           statuses=Incident.STATUSES, status_index=idx,
                           next_status=next_status, prev_status=prev_status,
                           available_controls=available_controls, available_risks=available_risks,
                           resolution_hours=hours)


def can_link():
    return current_user.is_authenticated and current_user.has_permission('write')


# ---------- state-changing actions ----------

@incidents_bp.route('/<int:incident_id>/status', methods=['POST'])
@login_required
@require_permission('write')
def change_status(incident_id):
    incident = _get_incident(incident_id)
    target = request.form.get('status', '')
    if target not in Incident.STATUSES:
        flash('Invalid status.', 'error')
        return redirect(url_for('incidents.incident_detail', incident_id=incident.id))
    cur_idx = Incident.STATUSES.index(incident.status)
    new_idx = Incident.STATUSES.index(target)
    if abs(new_idx - cur_idx) != 1:
        flash(f'Cannot move an incident from {incident.status} to {target}. Move one step at a time.', 'error')
        return redirect(url_for('incidents.incident_detail', incident_id=incident.id))

    summary = request.form.get('resolution_summary', '').strip()
    comment = request.form.get('comment', '').strip()
    old = incident.status
    if target == 'Closed':
        if summary:
            incident.resolution_summary = summary
        if not incident.resolution_summary:
            flash('A resolution summary is required to close an incident.', 'error')
            return redirect(url_for('incidents.incident_detail', incident_id=incident.id))
        incident.closed_at = datetime.utcnow()
    elif old == 'Closed':
        incident.closed_at = None  # reopened
    incident.status = target
    body = f'Status changed from {old} to {target}.'
    if comment:
        body += f'\n{comment}'
    _add_entry(incident, 'status_change', body)
    log_activity('updated', 'Incident', incident.title,
                 f'{current_user.name} moved incident "{incident.title}" from {old} to {target}')
    _notify_owner(incident, f'Incident {target}: {incident.title}', f'Status changed from {old} to {target}.')
    db.session.commit()
    flash(f'Incident moved to {target}.', 'success')
    return redirect(url_for('incidents.incident_detail', incident_id=incident.id))


@incidents_bp.route('/<int:incident_id>/notes', methods=['POST'])
@login_required
@require_permission('write')
def add_note(incident_id):
    incident = _get_incident(incident_id)
    body = request.form.get('body', '').strip()
    entry_type = request.form.get('entry_type', 'note')
    if entry_type not in ('note', 'action'):
        entry_type = 'note'
    if not body:
        flash('Note cannot be empty.', 'error')
    else:
        _add_entry(incident, entry_type, body[:5000])
        log_activity('updated', 'Incident', incident.title, f'{current_user.name} added a {entry_type} to incident "{incident.title}"')
        db.session.commit()
        flash('Timeline entry added.', 'success')
    return redirect(url_for('incidents.incident_detail', incident_id=incident.id))


@incidents_bp.route('/<int:incident_id>/controls/link', methods=['POST'])
@login_required
@require_permission('write')
def link_controls(incident_id):
    incident = _get_incident(incident_id)
    existing = {c.id for c in incident.controls}
    ids = {int(c) for c in request.form.getlist('control_ids') if c.isdigit()} - existing
    added = 0
    if ids:
        for control in _visible_controls(incident.organization_id).filter(Control.id.in_(ids)).all():
            incident.controls.append(control)
            added += 1
    if added:
        _add_entry(incident, 'action', f'Linked {added} control(s).')
        log_activity('updated', 'Incident', incident.title, f'{current_user.name} linked {added} control(s) to incident "{incident.title}"')
        db.session.commit()
    flash(f'{added} control(s) linked.', 'success' if added else 'info')
    return redirect(url_for('incidents.incident_detail', incident_id=incident.id))


@incidents_bp.route('/<int:incident_id>/controls/<int:control_id>/unlink', methods=['POST'])
@login_required
@require_permission('write')
def unlink_control(incident_id, control_id):
    incident = _get_incident(incident_id)
    control = next((c for c in incident.controls if c.id == control_id), None)
    if control is not None:
        incident.controls.remove(control)
        db.session.commit()
        flash('Control unlinked.', 'info')
    return redirect(url_for('incidents.incident_detail', incident_id=incident.id))


@incidents_bp.route('/<int:incident_id>/risks/link', methods=['POST'])
@login_required
@require_permission('write')
def link_risks(incident_id):
    incident = _get_incident(incident_id)
    existing = {r.id for r in incident.risks}
    ids = {int(r) for r in request.form.getlist('risk_ids') if r.isdigit()} - existing
    added = 0
    if ids:
        for risk in Risk.query.filter(Risk.organization_id == incident.organization_id, Risk.id.in_(ids)).all():
            incident.risks.append(risk)
            added += 1
    if added:
        _add_entry(incident, 'action', f'Linked {added} risk(s).')
        log_activity('updated', 'Incident', incident.title, f'{current_user.name} linked {added} risk(s) to incident "{incident.title}"')
        db.session.commit()
    flash(f'{added} risk(s) linked.', 'success' if added else 'info')
    return redirect(url_for('incidents.incident_detail', incident_id=incident.id))


@incidents_bp.route('/<int:incident_id>/risks/<int:risk_id>/unlink', methods=['POST'])
@login_required
@require_permission('write')
def unlink_risk(incident_id, risk_id):
    incident = _get_incident(incident_id)
    risk = next((r for r in incident.risks if r.id == risk_id), None)
    if risk is not None:
        incident.risks.remove(risk)
        db.session.commit()
        flash('Risk unlinked.', 'info')
    return redirect(url_for('incidents.incident_detail', incident_id=incident.id))


@incidents_bp.route('/<int:incident_id>/review', methods=['POST'])
@login_required
@require_permission('write')
def save_review(incident_id):
    incident = _get_incident(incident_id)
    incident.lessons_learned = request.form.get('lessons_learned', '').strip()
    incident.follow_up_actions = request.form.get('follow_up_actions', '').strip()
    incident.root_cause = request.form.get('root_cause', incident.root_cause or '').strip()
    if request.form.get('mark_complete') and (incident.lessons_learned or incident.follow_up_actions):
        incident.review_completed_at = datetime.utcnow()
        _add_entry(incident, 'action', 'Post-incident review completed.')
    elif not request.form.get('mark_complete'):
        incident.review_completed_at = None
    log_activity('updated', 'Incident', incident.title, f'{current_user.name} updated the post-incident review for "{incident.title}"')
    db.session.commit()
    flash('Post-incident review saved.', 'success')
    return redirect(url_for('incidents.incident_detail', incident_id=incident.id))


@incidents_bp.route('/<int:incident_id>/delete', methods=['POST'])
@login_required
@require_permission('delete')
def delete_incident(incident_id):
    incident = _get_incident(incident_id)
    title = incident.title
    incident.controls = []
    incident.risks = []
    db.session.delete(incident)
    log_activity('deleted', 'Incident', title)
    db.session.commit()
    flash(f'Incident "{title}" deleted.', 'success')
    return redirect(url_for('incidents.incidents'))
