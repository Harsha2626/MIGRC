from datetime import datetime, date
from flask import current_app

DATE_FORMATS = ['%Y-%m-%d', '%d %b %Y', '%d %B %Y']


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config.get('ALLOWED_EXTENSIONS', set())


def parse_date_safe(value):
    """Parse a free-text date string tried against known formats. Returns a date or None."""
    if not value:
        return None
    if isinstance(value, date):
        return value
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def timesince(dt):
    """Hand-rolled 'time ago' formatter, e.g. '2h ago', '3d ago', 'Just now'."""
    if not dt:
        return ''
    now = datetime.utcnow()
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return 'Just now'
    if seconds < 3600:
        return f'{int(seconds // 60)}m ago'
    if seconds < 86400:
        return f'{int(seconds // 3600)}h ago'
    if seconds < 2592000:
        return f'{int(seconds // 86400)}d ago'
    return dt.strftime('%d %b %Y')
