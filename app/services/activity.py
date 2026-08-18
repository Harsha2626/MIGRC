from flask_login import current_user
from app.models import db, ActivityLog


def log_activity(action, entity_type, entity_name, description=None):
    """Record a user action. Call right before the caller's own db.session.commit()."""
    user_name = current_user.name if current_user.is_authenticated else 'Someone'
    user_id = current_user.id if current_user.is_authenticated else None

    if description is None:
        description = f'{user_name} {action} {entity_type.lower()} "{entity_name}"'

    db.session.add(ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_name=entity_name,
        description=description,
    ))
