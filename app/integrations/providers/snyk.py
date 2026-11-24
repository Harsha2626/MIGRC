"""Snyk: open issues vs SLA (REST issues API, api.snyk.io only)."""
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests

from app.integrations import Check

HOST, VER, TIMEOUT, MAX_PAGES, SLA_DAYS = 'https://api.snyk.io', '2024-10-15', 30, 20, 30
KW = ['vulnerability', 'vulnerabilities', 'patch', 'secure development', 'technical vulnerabilit', 'penetration']


class Denied(Exception):
    pass


def _get(token, path, params=None):
    r = requests.get(HOST + path, params=params, timeout=TIMEOUT, allow_redirects=False,
                     headers={'Authorization': f'token {token}', 'Accept': 'application/vnd.api+json'})
    if r.status_code in (401, 403):
        raise Denied(f'HTTP {r.status_code}')
    r.raise_for_status()
    return r.json()


def _org(cfg):
    return quote(str(cfg.get('org_id', '')).strip(), safe='')


def validate(cfg):
    d = _get(cfg['token'], f'/rest/orgs/{_org(cfg)}', {'version': VER})
    return (d.get('data', {}).get('attributes') or {}).get('name') or cfg.get('org_id')


def _issues(cfg):
    """Open issues, paginated (capped at MAX_PAGES*100); returns (list, truncated)."""
    out, path, params = [], f'/rest/orgs/{_org(cfg)}/issues', {'version': VER, 'status': 'open', 'limit': 100}
    for _ in range(MAX_PAGES):
        d = _get(cfg['token'], path, params)
        out += d.get('data', [])
        nxt = (d.get('links') or {}).get('next')
        if not nxt:
            return out, False
        path, params = nxt if nxt.startswith('/rest/') else None, None  # relative links only: token stays on HOST
        if not path:
            return out, True
    return out, True


def scan(cfg):
    kw = KW
    try:
        issues, trunc = _issues(cfg)
    except Denied as e:
        d = f'Snyk API refused the token ({e}). Needs a token with view access to the org issues (REST API).'
        return [Check('Snyk: no open Critical issues', False, d, kw, 'Medium'),
                Check(f'Snyk: no open High issues older than {SLA_DAYS} days', False, d, kw, 'Medium')]
    sev = lambda i: ((i.get('attributes') or {}).get('effective_severity_level') or '').lower()
    name = lambda i: (i.get('attributes') or {}).get('title') or i.get('id')
    counts = {s: sum(1 for i in issues if sev(i) == s) for s in ('critical', 'high', 'medium', 'low')}
    cutoff = datetime.now(timezone.utc) - timedelta(days=SLA_DAYS)

    def old(i):
        try:
            return datetime.fromisoformat(i['attributes']['created_at'].replace('Z', '+00:00')) < cutoff
        except (KeyError, ValueError, AttributeError, TypeError):
            return False
    crit = [i for i in issues if sev(i) == 'critical']
    high = [i for i in issues if sev(i) == 'high' and old(i)]
    tot = ', '.join(f'{k}={v}' for k, v in counts.items()) + (' (truncated at cap)' if trunc else '')
    sample = lambda L: ', '.join(str(name(i)) for i in L[:5]) or 'none'
    return [
        Check('Snyk: no open Critical issues', not crit,
              f'Open issues by severity: {tot}. Critical open: {len(crit)} (e.g. {sample(crit)}).', kw, 'Critical'),
        Check(f'Snyk: no open High issues older than {SLA_DAYS} days', not high,
              f'Open issues by severity: {tot}. High open > {SLA_DAYS}d: {len(high)} (e.g. {sample(high)}).', kw, 'High'),
    ]


SPEC = {
    'key': 'snyk', 'name': 'Snyk', 'category': 'Vulnerability Scanners', 'icon': 'fas fa-bug', 'color': 'purple',
    'capabilities': ['Open Critical issues', 'High issues past SLA', 'Open issue totals by severity'],
    'fields': [{'name': 'token', 'label': 'API token', 'secret': True, 'placeholder': 'Snyk API token'},
               {'name': 'org_id', 'label': 'Organization ID', 'placeholder': 'Snyk org UUID'}],
    'validate': validate, 'scan': scan,
}
