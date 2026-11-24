"""PagerDuty: escalation policies, on-call schedules, long-open high-urgency incidents (api.pagerduty.com only)."""
from datetime import datetime, timedelta, timezone

import requests

from app.integrations import Check

HOST, TIMEOUT, OPEN_DAYS = 'https://api.pagerduty.com', 30, 7
KW = ['incident', 'on-call', 'escalation', 'response', 'availability', 'monitoring']


class Denied(Exception):
    pass


def _get(key, path, params=None):
    r = requests.get(HOST + path, params=params, timeout=TIMEOUT, allow_redirects=False,
                     headers={'Authorization': f'Token token={key}', 'Accept': 'application/vnd.pagerduty+json;version=2'})
    if r.status_code in (401, 403):
        raise Denied(f'HTTP {r.status_code}')
    r.raise_for_status()
    return r.json()


def validate(cfg):
    _get(cfg['api_key'], '/escalation_policies', {'limit': 1})
    return 'PagerDuty account'


def scan(cfg):
    k = cfg['api_key']
    try:
        pols = _get(k, '/escalation_policies', {'limit': 100}).get('escalation_policies', [])
        scheds = _get(k, '/schedules', {'limit': 100}).get('schedules', [])
        inc = _get(k, '/incidents', {'statuses[]': ['triggered', 'acknowledged'], 'urgencies[]': ['high'],
                                     'limit': 100}).get('incidents', [])
    except Denied as e:
        d = f'PagerDuty API refused the key ({e}). Needs a read-only REST API key.'
        return [Check(t, False, d, KW, 'Medium') for t in (
            'PagerDuty: escalation policies exist', 'PagerDuty: on-call schedules exist',
            f'PagerDuty: no high-urgency incidents open > {OPEN_DAYS} days')]
    cutoff = datetime.now(timezone.utc) - timedelta(days=OPEN_DAYS)

    def old(i):
        try:
            return datetime.fromisoformat(i['created_at'].replace('Z', '+00:00')) < cutoff
        except (KeyError, ValueError, AttributeError, TypeError):
            return False
    stale = [i for i in inc if old(i)]
    return [
        Check('PagerDuty: escalation policies exist', bool(pols), f'{len(pols)} escalation policy(ies) found.', KW, 'High'),
        Check('PagerDuty: on-call schedules exist', bool(scheds), f'{len(scheds)} on-call schedule(s) found.', KW, 'Medium'),
        Check(f'PagerDuty: no high-urgency incidents open > {OPEN_DAYS} days', not stale,
              f'{len(stale)} high-urgency incident(s) open more than {OPEN_DAYS} days (of {len(inc)} open).', KW, 'High'),
    ]


SPEC = {
    'key': 'pagerduty', 'name': 'PagerDuty', 'category': 'Monitoring & Incident', 'icon': 'fas fa-bell', 'color': 'green',
    'capabilities': ['Escalation policies', 'On-call schedules', 'Long-open high-urgency incidents'],
    'fields': [{'name': 'api_key', 'label': 'REST API key (read-only)', 'secret': True, 'placeholder': 'PagerDuty API key'}],
    'validate': validate, 'scan': scan,
}
