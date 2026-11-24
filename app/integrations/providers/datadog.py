"""Datadog: monitors exist, none stuck in Alert, notification channels (fixed Datadog API hosts only)."""
from datetime import datetime, timedelta, timezone

import requests

from app.integrations import Check

SITES = ('api.datadoghq.com', 'api.datadoghq.eu', 'api.us3.datadoghq.com', 'api.us5.datadoghq.com',
         'api.ap1.datadoghq.com')
TIMEOUT, ALERT_DAYS = 30, 7
KW = ['monitoring', 'alert', 'logging', 'incident', 'detect', 'audit']


class Denied(Exception):
    pass


def _get(cfg, path, params=None):
    site = str(cfg.get('site', '')).strip().lower()
    if site not in SITES:  # allowlist: keys are only ever sent to Datadog hosts
        raise ValueError('Site must be one of: ' + ', '.join(SITES))
    r = requests.get(f'https://{site}{path}', params=params, timeout=TIMEOUT, allow_redirects=False,
                     headers={'DD-API-KEY': cfg['api_key'], 'DD-APPLICATION-KEY': cfg['app_key']})
    if r.status_code in (401, 403):
        raise Denied(f'HTTP {r.status_code}')
    r.raise_for_status()
    return r.json()


def validate(cfg):
    _get(cfg, '/api/v1/validate')
    _get(cfg, '/api/v1/monitor', {'page_size': 1, 'page': 0})  # also proves the application key
    return cfg['site'].strip().lower()


def scan(cfg):
    try:
        mons = _get(cfg, '/api/v1/monitor', {'page_size': 1000, 'page': 0})
    except Denied as e:
        d = f'Datadog API refused the keys ({e}). Needs an API key and an application key with monitors_read.'
        return [Check(t, False, d, KW, 'Medium') for t in (
            'Datadog: at least one monitor exists', f'Datadog: no monitors in Alert state > {ALERT_DAYS} days',
            'Datadog: alert notification channel configured')]
    cutoff = datetime.now(timezone.utc) - timedelta(days=ALERT_DAYS)

    def stale(m):
        if m.get('overall_state') != 'Alert':
            return False
        try:
            return datetime.fromisoformat(m['overall_state_modified'].replace('Z', '+00:00')) < cutoff
        except (KeyError, ValueError, AttributeError, TypeError):
            return False
    old = [m for m in mons if stale(m)]
    notif = [m for m in mons if '@' in (m.get('message') or '')]  # @slack-/@pagerduty-/@email handles
    return [
        Check('Datadog: at least one monitor exists', bool(mons), f'{len(mons)} monitor(s) found.', KW, 'High'),
        Check(f'Datadog: no monitors in Alert state > {ALERT_DAYS} days', not old,
              f'{len(old)} of {len(mons)} monitor(s) in Alert state for more than {ALERT_DAYS} days.', KW, 'High'),
        Check('Datadog: alert notification channel configured', bool(notif),
              f'{len(notif)} of {len(mons)} monitor(s) notify a channel/handle.', KW, 'Medium'),
    ]


SPEC = {
    'key': 'datadog', 'name': 'Datadog', 'category': 'Monitoring & Incident', 'icon': 'fas fa-dog', 'color': 'purple',
    'capabilities': ['Monitors configured', 'Long-standing Alert monitors', 'Alert notification channels'],
    'fields': [{'name': 'api_key', 'label': 'API key', 'secret': True, 'placeholder': 'Datadog API key'},
               {'name': 'app_key', 'label': 'Application key', 'secret': True, 'placeholder': 'Datadog application key'},
               {'name': 'site', 'label': 'Site (API host)', 'placeholder': 'api.datadoghq.com'}],
    'validate': validate, 'scan': scan,
}
