"""Cloudflare (API token). Token is only sent to api.cloudflare.com."""
import requests

from app.integrations import Check

TIMEOUT = 20
API = 'https://api.cloudflare.com/client/v4'
MAX_ZONES = 50


def _get(cfg, path, **kw):
    r = requests.request('GET', API + path, headers={'Authorization': f'Bearer {cfg.get("api_token", "")}',
                                                     'Accept': 'application/json'},
                         timeout=TIMEOUT, allow_redirects=False, **kw)
    r.raise_for_status()
    return r.json()


def validate(cfg):
    return _get(cfg, '/user/tokens/verify')['result']['status']


def _names(bad, n=10):
    return f' ({", ".join(bad[:n])}{"..." if len(bad) > n else ""})' if bad else ''


def scan(cfg):
    try:
        zones, page = [], 1
        while len(zones) < MAX_ZONES:
            j = _get(cfg, '/zones', params={'per_page': 50, 'page': page})
            zones += j.get('result') or []
            if page >= (j.get('result_info') or {}).get('total_pages', 1):
                break
            page += 1
        zones = zones[:MAX_ZONES]
    except requests.HTTPError as e:
        code = e.response.status_code
        d = f'Could not list zones: API returned {code}' + (' (token lacks Zone:Read).' if code in (401, 403) else '.')
        return [Check('Cloudflare: zones accessible', False, d, ['network security'], 'Low')]
    except (requests.RequestException, ValueError):
        return [Check('Cloudflare: zones accessible', False, 'Could not list zones: request failed.',
                      ['network security'], 'Low')]
    if not zones:
        return [Check('Cloudflare: zones accessible', False, 'No zones visible to this token.',
                      ['network security'], 'Low')]
    cache = {}

    def settings(z):
        if z['id'] not in cache:
            cache[z['id']] = {s['id']: s.get('value') for s in _get(cfg, f'/zones/{z["id"]}/settings')['result']}
        return cache[z['id']]

    def per_zone(title, kw, sev, ok_fn, what):
        bad = []
        try:
            for z in zones:
                if not ok_fn(z):
                    bad.append(z['name'])
        except requests.HTTPError as e:
            code = e.response.status_code
            return Check(title, False, f'Could not evaluate: API returned {code}'
                         + (' (token lacks permission for this setting).' if code in (401, 403) else '.'), kw, 'Low')
        except (requests.RequestException, ValueError, KeyError):
            return Check(title, False, 'Could not evaluate: request failed or returned unexpected data.', kw, 'Low')
        return Check(title, not bad, f'{len(zones)} zone(s) checked; {what} missing on {len(bad)}{_names(bad)}.',
                     kw, sev)

    def waf(z):
        try:
            j = _get(cfg, f'/zones/{z["id"]}/rulesets/phases/http_request_firewall_managed/entrypoint')
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return False
            raise
        return any(r.get('enabled', True) for r in (j.get('result') or {}).get('rules') or [])

    def hsts(z):
        return bool(((settings(z).get('security_header') or {}).get('strict_transport_security') or {}).get('enabled'))

    net = ['network security', 'encryption in transit', 'transmission', 'tls']
    return [
        per_zone('Cloudflare: SSL mode is Full (strict)', net, 'High',
                 lambda z: settings(z).get('ssl') == 'strict', 'Full (strict)'),
        per_zone('Cloudflare: Always Use HTTPS enabled', net, 'Medium',
                 lambda z: settings(z).get('always_use_https') == 'on', 'Always Use HTTPS'),
        per_zone('Cloudflare: minimum TLS version >= 1.2', net, 'High',
                 lambda z: float(settings(z).get('min_tls_version') or 0) >= 1.2, 'TLS >= 1.2'),
        per_zone('Cloudflare: WAF managed rules enabled', ['network security', 'firewall', 'vulnerability'],
                 'High', waf, 'managed WAF rules'),
        per_zone('Cloudflare: DNSSEC enabled', ['network security', 'dns', 'integrity'], 'Medium',
                 lambda z: _get(cfg, f'/zones/{z["id"]}/dnssec')['result'].get('status') == 'active', 'DNSSEC'),
        per_zone('Cloudflare: HSTS enabled', net, 'Medium', hsts, 'HSTS'),
    ]


SPEC = {
    'key': 'cloudflare', 'name': 'Cloudflare', 'category': 'SaaS Application', 'icon': 'fas fa-shield-alt',
    'color': 'orange',
    'capabilities': ['SSL/TLS mode', 'Always Use HTTPS', 'Minimum TLS', 'WAF managed rules', 'DNSSEC', 'HSTS'],
    'fields': [{'name': 'api_token', 'label': 'API token (read-only)', 'secret': True, 'placeholder': ''}],
    'validate': validate, 'scan': scan,
}
