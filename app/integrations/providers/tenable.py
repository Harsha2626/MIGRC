"""Tenable.io: open Critical/High vulns and stale assets (cloud.tenable.com only, workbenches API)."""
import time
from datetime import datetime, timedelta, timezone

import requests

from app.integrations import Check

HOST, TIMEOUT, SLA_DAYS = 'https://cloud.tenable.com', 30, 30
KW = ['vulnerability', 'vulnerabilities', 'patch', 'technical vulnerabilit', 'penetration', 'secure development']
KW_ASSET = ['vulnerability', 'technical vulnerabilit', 'asset', 'inventory', 'scan']
SEV = {'Critical': 4, 'High': 3}


class Denied(Exception):
    pass


def _get(cfg, path, params=None):
    r = requests.get(HOST + path, params=params, timeout=TIMEOUT, allow_redirects=False,
                     headers={'X-ApiKeys': f'accessKey={cfg["access_key"]}; secretKey={cfg["secret_key"]}',
                              'Accept': 'application/json'})
    if r.status_code in (401, 403):
        raise Denied(f'HTTP {r.status_code}')
    r.raise_for_status()
    return r.json()


def validate(cfg):
    d = _get(cfg, '/session')
    return d.get('name') or d.get('username') or d.get('email') or 'Tenable.io'


def _vulns(cfg, sev, older_than=None):
    # filter.search_type=and: severity AND (optionally) first_found before cutoff
    p = {'date_range': 365, 'filter.search_type': 'and', 'filter.0.filter': 'severity', 'filter.0.quality': 'eq',
         'filter.0.value': sev, 'filter.1.filter': 'state', 'filter.1.quality': 'eq', 'filter.1.value': 'open'}
    if older_than:
        p.update({'filter.2.filter': 'first_found', 'filter.2.quality': 'lt', 'filter.2.value': older_than})
    return _get(cfg, '/workbenches/vulnerabilities', p).get('vulnerabilities', [])


def _vuln_check(cfg, title, sev, older_than, level):
    try:
        v = [x for x in _vulns(cfg, sev, older_than) if x.get('severity', SEV[sev]) == SEV[sev]]
    except Denied as e:
        return Check(title, False, f'Tenable.io refused the call ({e}). Needs API keys of a user with Scan Operator '
                     'or higher (vulnerability read) permissions.', KW, 'Medium')
    n = sum(x.get('count', 1) for x in v)
    names = ', '.join(f'{x.get("plugin_name", "?")} (plugin {x.get("plugin_id")})' for x in v[:5]) or 'none'
    return Check(title, not v, f'{sev} open findings: {n} across {len(v)} plugin(s) (e.g. {names}).', KW, level)


def _ts(a):
    for k in ('last_scan_time', 'last_seen'):
        s = a.get(k)
        if s:
            try:
                return datetime.fromisoformat(str(s).replace('Z', '+00:00'))
            except ValueError:
                pass
    return None


def scan(cfg):
    cutoff = int(time.time()) - SLA_DAYS * 86400
    stale_title = f'Tenable: assets scanned in last {SLA_DAYS} days'
    out = [_vuln_check(cfg, 'Tenable: no Critical vulnerabilities open', 'Critical', None, 'Critical'),
           _vuln_check(cfg, f'Tenable: no High vulnerabilities open > {SLA_DAYS} days', 'High', cutoff, 'High')]
    try:
        assets = _get(cfg, '/assets').get('assets', [])
    except Denied as e:
        return out + [Check(stale_title, False, f'Tenable.io refused the call ({e}). Needs permission to list assets.',
                            KW_ASSET, 'Medium')]
    lim = datetime.now(timezone.utc) - timedelta(days=SLA_DAYS)
    stale = [a for a in assets if (_ts(a) or datetime.min.replace(tzinfo=timezone.utc)) < lim]
    def label(a):
        v = a.get('fqdn') or a.get('hostname') or a.get('id') or '?'
        return str(v[0] if isinstance(v, list) and v else v)
    nm = ', '.join(label(a) for a in stale[:5]) or 'none'
    return out + [Check(stale_title, not stale, f'{len(assets)} asset(s); not scanned in {SLA_DAYS}d: {len(stale)} (e.g. {nm}).',
                        KW_ASSET, 'Medium')]


SPEC = {
    'key': 'tenable', 'name': 'Tenable.io', 'category': 'Vulnerability Scanners', 'icon': 'fas fa-shield-virus',
    'color': 'teal',
    'capabilities': ['Open Critical vulnerabilities', 'High vulnerabilities past SLA', 'Stale asset scans'],
    'fields': [{'name': 'access_key', 'label': 'Access key', 'placeholder': 'Tenable.io access key'},
               {'name': 'secret_key', 'label': 'Secret key', 'secret': True, 'placeholder': 'Tenable.io secret key'}],
    'validate': validate, 'scan': scan,
}
