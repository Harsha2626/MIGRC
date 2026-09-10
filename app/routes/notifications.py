from flask import Blueprint, render_template, redirect, url_for, request, g
from flask_login import login_required, current_user
from app.models import db, Notification

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/notifications')
@login_required
def notifications():
    org_id = g.current_org.id if g.current_org else -1
    all_notifications = (Notification.query
        .filter_by(user_id=current_user.id, organization_id=org_id)
        .order_by(Notification.created_at.desc())
        .limit(100).all())
    return render_template('notifications.html', page='notifications', notifications=all_notifications)


@notifications_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    org_id = g.current_org.id if g.current_org else -1
    notif = Notification.query.filter_by(id=notification_id, user_id=current_user.id, organization_id=org_id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return redirect(notif.link or url_for('notifications.notifications'))


@notifications_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    org_id = g.current_org.id if g.current_org else -1
    Notification.query.filter_by(user_id=current_user.id, organization_id=org_id, is_read=False).update({'is_read': True})
    db.session.commit()
    return redirect(request.referrer or url_for('notifications.notifications'))
