from datetime import date, timedelta
from flask import current_app
from app.models import db, User, Notification, Policy, Vendor, Audit

TYPE_ICONS = {
    'deadline_approaching': 'fa-clock',
    'evidence_rejected': 'fa-file-circle-xmark',
    'risk_escalated': 'fa-triangle-exclamation',
    'policy_review_due': 'fa-file-shield',
    'finding_assigned': 'fa-magnifying-glass-chart',
}


def _create_if_new(user_id, type_, title, message, link, dedupe_key):
    if dedupe_key and Notification.query.filter_by(user_id=user_id, dedupe_key=dedupe_key).first():
        return None
    notif = Notification(user_id=user_id, type=type_, title=title, message=message, link=link, dedupe_key=dedupe_key)
    db.session.add(notif)
    return notif


def _maybe_email(notifications):
    if not current_app.config.get('MAIL_ENABLED'):
        return
    from app.services.mail import send_notification_email
    for n in notifications:
        try:
            send_notification_email(n.user, n.title, n.message or '')
        except Exception:
            current_app.logger.exception('Failed to send notification email for notification %s', n.id)


def notify_all_users(type_, title, message, link=None, dedupe_key=None):
    """One notification per active user. dedupe_key (if given) is scoped per-user so re-running a
    daily check never double-notifies the same person about the same underlying event."""
    created = []
    for user in User.query.filter_by(is_active_user=True).all():
        per_user_key = f'{dedupe_key}:{user.id}' if dedupe_key else None
        n = _create_if_new(user.id, type_, title, message, link, per_user_key)
        if n:
            created.append(n)
    if created:
        db.session.commit()
        _maybe_email(created)
    return created


def notify_evidence_rejected(evidence):
    user = evidence.uploaded_by
    if not user:
        return
    mapping = evidence.evidence_mappings.first()
    link = f'/compliance/{mapping.control.framework_id}/control/{mapping.control_id}' if mapping else '/compliance'
    _create_if_new(
        user.id, 'evidence_rejected',
        f'Evidence rejected: {evidence.title}',
        evidence.review_notes or 'Your uploaded evidence was rejected during review.',
        link,
        dedupe_key=f'evidence_rejected:{evidence.id}:{evidence.reviewed_at}',
    )
    db.session.commit()


def notify_risk_escalated(risk):
    if risk.impact != 'Critical':
        return
    notify_all_users(
        'risk_escalated', f'Critical risk: {risk.title}',
        f'"{risk.title}" is now rated Critical impact and needs attention.',
        link='/risks',
        dedupe_key=f'risk_escalated:{risk.id}',
    )


def notify_finding_assigned(finding):
    notify_all_users(
        'finding_assigned', 'New audit finding logged',
        finding.description[:150],
        link=f'/audits/{finding.audit_id}',
        dedupe_key=f'finding_assigned:{finding.id}',
    )


def ensure_notifications_for_today():
    """Lazy daily check for deadlines approaching within 7 days — policy reviews, vendor
    reassessments, audits wrapping up. Safe to call on every dashboard load (dedupe_key guards it)."""
    today = date.today()
    horizon = today + timedelta(days=7)

    from app.utils import parse_date_safe

    for policy in Policy.query.filter(Policy.status == 'Published').all():
        d = parse_date_safe(policy.next_review)
        if d and today <= d <= horizon:
            notify_all_users(
                'policy_review_due', f'Policy review due: {policy.name}',
                f'"{policy.name}" is due for review on {d.strftime("%d %b %Y")}.',
                link=f'/policies/{policy.id}',
                dedupe_key=f'policy_review_due:{policy.id}:{d}',
            )

    for vendor in Vendor.query.all():
        d = parse_date_safe(vendor.next_assessment)
        if d and today <= d <= horizon:
            notify_all_users(
                'deadline_approaching', f'Vendor assessment due: {vendor.name}',
                f'{vendor.name} is due for reassessment on {d.strftime("%d %b %Y")}.',
                link=f'/vendors/{vendor.id}',
                dedupe_key=f'vendor_assessment_due:{vendor.id}:{d}',
            )

    for audit in Audit.query.filter(Audit.status != 'Completed').all():
        d = parse_date_safe(audit.end_date)
        if d and today <= d <= horizon:
            notify_all_users(
                'deadline_approaching', f'Audit wrapping up soon: {audit.name}',
                f'{audit.name} is scheduled to end on {d.strftime("%d %b %Y")}.',
                link=f'/audits/{audit.id}',
                dedupe_key=f'audit_end_due:{audit.id}:{d}',
            )
