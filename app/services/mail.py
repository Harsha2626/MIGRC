from flask_mail import Message


def send_notification_email(user, subject, body):
    """Best-effort email alert. Caller (notifications.py) already checks MAIL_ENABLED and
    catches exceptions, so this stays simple."""
    if not user or not user.email:
        return
    from app import mail
    msg = Message(subject=f'[MIGRC] {subject}', recipients=[user.email], body=body)
    mail.send(msg)
