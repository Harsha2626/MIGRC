"""Auth0 (Management API, client-credentials). Credentials only ever go to the validated *.auth0.com tenant host."""
import re

import requests

from app.integrations import Check

TIMEOUT = 20
DOMAIN_RE = re.compile(r'^[a-z0-9-]+(\.[a-z0-9-]+)*\.auth0\.com$')
PW_RANK = {'none': 0, 'low': 1, 'fair': 2, 'good': 3, 'excellent': 4}


def _domain(cfg):
    d = (cfg.get('domain') or '').strip().lower()
    if not DOMAIN_RE.match(d):
        raise ValueError('Auth0 domain must look like your-tenant.us.auth0.com')
    return d


def _token(cfg):
    d = _domain(cfg)
    r = requests.request('POST', f'https://{d}/oauth/token', timeout=TIMEOUT, allow_redirects=False, json={
        'grant_type': 'client_credentials', 'client_id': cfg.get('client_id', ''),
        'client_secret': cfg.get('client_secret', ''), 'audience': f'https://{d}/api/v2/'})
    r.raise_for_status()
    return d, r.json()['access_token']


def validate(cfg):
    d, _ = _token(cfg)
    return d


def _guard(title, kw, sev, fn):
    try:
        ok, detail = fn()
        return Check(title, ok, detail, kw, sev)
    except requests.HTTPError as e:
        code = e.response.status_code
        why = ' (the M2M application lacks the required Management API scope).' if code in (401, 403) else '.'
        return Check(title, False, f'Could not evaluate: API returned {code}{why}', kw, 'Low')
    except (requests.RequestException, ValueError, KeyError):
        return Check(title, False, 'Could not evaluate: request failed or returned unexpected data.', kw, 'Low')


def scan(cfg):
    try:
        d, tok = _token(cfg)
    except (requests.RequestException, ValueError, KeyError):
        return [Check('Auth0: Management API reachable', False,
                      'Could not obtain a Management API token (check domain, client id/secret and M2M grant).',
                      ['authentication'], 'Low')]
    h = {'Authorization': f'Bearer {tok}', 'Accept': 'application/json'}
    api = f'https://{d}/api/v2'

    def get(path, **kw):
        r = requests.request('GET', api + path, headers=h, timeout=TIMEOUT, allow_redirects=False, **kw)
        r.raise_for_status()
        return r.json()

    def mfa():
        on = [f['name'] for f in get('/guardian/factors') if f.get('enabled')]
        return bool(on), f'Enabled MFA factors: {", ".join(on) or "none"}.'

    def flag(path, label):
        def run():
            on = bool(get(path).get('enabled'))
            return on, f'{label} is {"enabled" if on else "disabled"}.'
        return run

    def pw():
        conns, page = [], 0
        while True:
            batch = get('/connections', params={'strategy': 'auth0', 'per_page': 100, 'page': page})
            conns += batch
            if len(batch) < 100 or page >= 20:
                break
            page += 1
        weak = [c['name'] for c in conns
                if PW_RANK.get(((c.get('options') or {}).get('passwordPolicy')) or 'none', 0) < PW_RANK['good']]
        return bool(conns) and not weak, (f'{len(conns)} database connection(s); below "good" password policy: '
                                          f'{len(weak)}' + (f' ({", ".join(weak[:10])}).' if weak else '.'))

    def logs():
        active = [s for s in get('/log-streams') if s.get('status') == 'active']
        return bool(active), f'{len(active)} active log stream(s) exporting tenant logs.'

    return [
        _guard('Auth0: MFA factors enabled', ['multi-factor', 'mfa', 'authentication'], 'High', mfa),
        _guard('Auth0: brute-force protection enabled', ['authentication', 'password', 'user access'], 'High',
               flag('/attack-protection/brute-force-protection', 'Brute-force protection')),
        _guard('Auth0: breached-password detection enabled', ['password', 'authentication'], 'Medium',
               flag('/attack-protection/breached-password-detection', 'Breached-password detection')),
        _guard('Auth0: database connection password policy >= good', ['password', 'authentication'], 'Medium', pw),
        _guard('Auth0: tenant log streaming configured', ['logging', 'monitoring', 'audit log'], 'Medium', logs),
    ]


SPEC = {
    'key': 'auth0', 'name': 'Auth0', 'category': 'Identity Providers', 'icon': 'fas fa-lock', 'color': 'orange',
    'capabilities': ['MFA factors', 'Brute-force protection', 'Breached-password detection', 'Password policy',
                     'Log streams'],
    'fields': [
        {'name': 'domain', 'label': 'Auth0 domain', 'placeholder': 'your-tenant.us.auth0.com'},
        {'name': 'client_id', 'label': 'M2M client ID', 'placeholder': ''},
        {'name': 'client_secret', 'label': 'M2M client secret', 'secret': True, 'placeholder': ''}],
    'validate': validate, 'scan': scan,
}
