"""1Password Business (Events API bearer token). Token is only sent to events.1password.com. No names/emails in output."""
from datetime import datetime, timedelta, timezone

import requests

from app.integrations import Check

TIMEOUT = 20
BASE = 'https://events.1password.com'
FAIL_LIMIT = 20       # failed sign-ins in 7 days before the check fails
SHARE_LIMIT = 25      # item-sharing events in 7 days before the check fails
BAD_CATS = ('credentials_failed', 'mfa_failed', 'firewall_failed', 'sso_failed', 'modern_version_failed')
MFA_WORDS = ('mfa', '2fa', 'two_factor', 'totp')


def _post(cfg, path, body=None):
    r = requests.request('POST', BASE + path, json=body, timeout=TIMEOUT, allow_redirects=False,
                         headers={'Authorization': f'Bearer {cfg.get("token", "")}', 'Accept': 'application/json'})
    r.raise_for_status()
    return r.json()


def _events(cfg, path):
    start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
    items = _post(cfg, path, {'limit': 1000, 'start_time': start}).get('items')
    if not isinstance(items, list):
        raise ValueError('unexpected data')
    return items


def validate(cfg):
    _post(cfg, '/api/v1/signinattempts', {'limit': 1})
    return '1Password Events API'


def _guard(title, kw, sev, fn):
    try:
        ok, detail = fn()
        return Check(title, ok, detail, kw, sev)
    except requests.HTTPError as e:
        code = e.response.status_code
        why = ' (token lacks the required event feature access).' if code in (401, 403) else '.'
        return Check(title, False, f'Could not evaluate: API returned {code}{why}', kw, 'Low')
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return Check(title, False, 'Could not evaluate: request failed or returned unexpected data.', kw, 'Low')


def scan(cfg):
    def signins():
        ev = _events(cfg, '/api/v1/signinattempts')
        bad = [e for e in ev if e.get('category') in BAD_CATS]
        return len(bad) < FAIL_LIMIT, (f'{len(ev)} sign-in attempt(s) in the last 7 days; failed or blocked: '
                                       f'{len(bad)} (threshold {FAIL_LIMIT}).')

    def mfa():
        ev = _events(cfg, '/api/v1/auditevents')
        off = [e for e in ev if any(w in str(e.get('object_type', '')).lower() for w in MFA_WORDS)
               and str(e.get('action', '')).lower() in ('delete', 'disable', 'remove', 'reset')]
        return not off, f'{len(ev)} audit event(s) in the last 7 days; MFA disabled/removed/reset events: {len(off)}.'

    def sharing():
        ev = _events(cfg, '/api/v1/itemusages')
        sh = [e for e in ev if str(e.get('action', '')).lower() in ('share', 'export')]
        return len(sh) < SHARE_LIMIT, (f'{len(ev)} item usage event(s) in the last 7 days; shared/exported: '
                                       f'{len(sh)} (threshold {SHARE_LIMIT}).')

    return [
        _guard('1Password: failed/suspicious sign-in volume', ['authentication', 'logging', 'monitoring'], 'Medium',
               signins),
        _guard('1Password: MFA not disabled (audit events)', ['multi-factor', 'mfa', 'authentication'], 'High', mfa),
        _guard('1Password: item-sharing events within threshold', ['data sharing', 'access', 'data leak'], 'Medium',
               sharing),
    ]


SPEC = {
    'key': 'onepassword', 'name': '1Password Business', 'category': 'Identity Providers', 'icon': 'fas fa-key',
    'color': 'blue',
    'capabilities': ['Failed sign-in volume', 'MFA changes (audit events)', 'Item sharing events'],
    'fields': [{'name': 'token', 'label': 'Events API bearer token', 'secret': True, 'placeholder': ''}],
    'validate': validate, 'scan': scan,
}
