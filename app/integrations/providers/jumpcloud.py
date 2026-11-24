"""JumpCloud (API key). Key is only sent to the two official console hosts."""
import requests

from app.integrations import Check

TIMEOUT = 20
HOSTS = ('console.jumpcloud.com', 'console.eu.jumpcloud.com')
MAX_GROUPS = 50


def _host(cfg):
    h = (cfg.get('host') or 'console.jumpcloud.com').strip().lower()
    if h not in HOSTS:
        raise ValueError('JumpCloud host must be console.jumpcloud.com or console.eu.jumpcloud.com')
    return h


def _get(cfg, path, **kw):
    r = requests.request('GET', f'https://{_host(cfg)}{path}', headers={
        'x-api-key': cfg.get('api_key', ''), 'Accept': 'application/json'}, timeout=TIMEOUT,
        allow_redirects=False, **kw)
    r.raise_for_status()
    return r.json()


def _all(cfg, path, cap=100):
    """v1 pagination (skip/limit, {'results': [...]})."""
    out, skip = [], 0
    for _ in range(cap):
        b = _get(cfg, path, params={'limit': 100, 'skip': skip}).get('results') or []
        out += b
        if len(b) < 100:
            break
        skip += 100
    return out


def validate(cfg):
    _get(cfg, '/api/systemusers', params={'limit': 1})
    return _host(cfg)


def _guard(title, kw, sev, fn):
    try:
        ok, detail = fn()
        return Check(title, ok, detail, kw, sev)
    except requests.HTTPError as e:
        code = e.response.status_code
        why = ' (API key lacks permission).' if code in (401, 403) else '.'
        return Check(title, False, f'Could not evaluate: API returned {code}{why}', kw, 'Low')
    except (requests.RequestException, ValueError, KeyError):
        return Check(title, False, 'Could not evaluate: request failed or returned unexpected data.', kw, 'Low')


def _ids(items, n=10):
    return f' ({", ".join(items[:n])}{"..." if len(items) > n else ""})' if items else ''


def scan(cfg):
    try:
        _host(cfg)
    except ValueError as e:
        return [Check('JumpCloud: API reachable', False, str(e), ['authentication'], 'Low')]
    cache = {}

    def users():
        if 'u' not in cache:
            cache['u'] = _all(cfg, '/api/systemusers')
        return cache['u']

    def active():
        return [u for u in users() if u.get('state', 'ACTIVATED') == 'ACTIVATED' and not u.get('suspended')]

    def mfa():
        a = active()
        bad = [u.get('username', u['_id']) for u in a if not (u.get('mfa') or {}).get('configured')
               and not u.get('totp_enabled')]
        return not bad, f'{len(a)} active user(s); without MFA enrolled: {len(bad)}{_ids(bad)}.'

    def pw():
        a = active()
        bad = [u.get('username', u['_id']) for u in a if u.get('password_never_expires') or u.get('passwordless')]
        return not bad, f'{len(a)} active user(s); never-expiring/passwordless: {len(bad)}{_ids(bad)}.'

    def groups():
        inactive = {u['_id']: u.get('username', u['_id']) for u in users()
                    if u.get('suspended') or u.get('state') in ('SUSPENDED',)}
        hits = set()
        gs = _get(cfg, '/api/v2/usergroups', params={'limit': MAX_GROUPS})
        for g in gs[:MAX_GROUPS]:
            for m in _get(cfg, f'/api/v2/usergroups/{g["id"]}/members', params={'limit': 100}):
                uid = (m.get('to') or {}).get('id')
                if uid in inactive:
                    hits.add(inactive[uid])
        return not hits, (f'{len(inactive)} suspended user(s); still in groups: {len(hits)}{_ids(sorted(hits))} '
                          f'(first {MAX_GROUPS} groups checked).')

    def fde():
        systems = _all(cfg, '/api/systems')
        bad = [s.get('hostname') or s['_id'] for s in systems if not (s.get('fde') or {}).get('active')]
        return not bad, f'{len(systems)} system(s); without disk encryption: {len(bad)}{_ids(bad)}.'

    return [
        _guard('JumpCloud: all active users enrolled in MFA', ['multi-factor', 'mfa', 'authentication'], 'High', mfa),
        _guard('JumpCloud: no passwordless / never-expiring passwords', ['password', 'authentication'], 'Medium', pw),
        _guard('JumpCloud: suspended users removed from groups', ['user access', 'deprovision', 'offboarding',
                                                                  'access rights'], 'Medium', groups),
        _guard('JumpCloud: systems have disk encryption', ['encryption', 'endpoint', 'data at rest'], 'High', fde),
    ]


SPEC = {
    'key': 'jumpcloud', 'name': 'JumpCloud', 'category': 'Identity Providers', 'icon': 'fas fa-cloud', 'color': 'green',
    'capabilities': ['User MFA enrollment', 'Password policy', 'Suspended-user group membership', 'Disk encryption'],
    'fields': [
        {'name': 'api_key', 'label': 'API key', 'secret': True, 'placeholder': ''},
        {'name': 'host', 'label': 'Console host (optional)', 'placeholder': 'console.jumpcloud.com or console.eu.jumpcloud.com'}],
    'validate': validate, 'scan': scan,
}
