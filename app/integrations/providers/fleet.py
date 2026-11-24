"""Fleet device management. Self-hosted URL, so the host is SSRF-guarded (the API token is sent there)."""
import ipaddress
import re
import socket
from urllib.parse import urlparse

import requests

from app.integrations import Check
from app.integrations.providers.kandji import MAX_PAGES, get_json, mdm_checks

BAD_SUFFIX = ('.local', '.localhost', '.internal', '.lan', '.home', '.corp', '.intranet', '.arpa')
POLICY_KINDS = (  # fleet policy name substring -> (check title, keywords, severity)
    ('firewall', 'firewall enabled (Fleet policies)', ['firewall', 'endpoint', 'device', 'network security'], 'Medium'),
    ('screen', 'screen lock configured (Fleet policies)', ['screen lock', 'session', 'endpoint', 'device', 'inactivity'], 'Medium'),
    ('antivirus', 'antivirus/EDR present (Fleet policies)', ['malware', 'antivirus', 'endpoint', 'anti-virus'], 'High'))


def _private(ip):
    return not ipaddress.ip_address(ip.split('%')[0]).is_global


def base_url(cfg):
    u = urlparse((cfg.get('url') or '').strip())
    h = (u.hostname or '').lower()
    if (u.scheme != 'https' or u.username or u.password or u.port not in (None, 443) or not re.fullmatch(r'[a-z0-9.-]+', h)
            or h == 'localhost' or h.endswith(BAD_SUFFIX) or '.' not in h or h.startswith(('.', '-')) or '..' in h
            or not re.search(r'[a-z]', h.rsplit('.', 1)[1])):  # last label non-numeric => not an IPv4 literal/decimal form
        raise ValueError('Fleet URL must be https://<public hostname>')
    # shortcut: resolve-then-connect leaves a DNS-rebinding window; pin the IP if this is exposed to untrusted tenants
    if any(_private(ai[4][0]) for ai in socket.getaddrinfo(h, 443, proto=socket.IPPROTO_TCP)):
        raise ValueError('Fleet host resolves to a non-public address')
    return f'https://{h}/api/v1/fleet'


def _h(cfg):
    return {'Authorization': f"Bearer {cfg['api_token']}", 'Accept': 'application/json'}


def validate(cfg):
    b = base_url(cfg)
    get_json(f'{b}/hosts', _h(cfg), params={'per_page': 1})
    return urlparse(b).hostname


def scan(cfg):
    b, h, rows = base_url(cfg), _h(cfg), []
    for page in range(MAX_PAGES):
        got = get_json(f'{b}/hosts', h, params={'per_page': 100, 'page': page}).get('hosts') or []
        rows += got
        if len(got) < 100:
            break
    devs = [{'name': f"{r.get('hostname') or r.get('id')} ({r.get('hardware_serial') or '?'})",
             'platform': r.get('platform'), 'os': r.get('os_version'), 'seen': r.get('seen_time'),
             'enc': r.get('disk_encryption_enabled')} for r in rows]  # null when Fleet doesn't know -> skipped
    checks = mdm_checks('Fleet', devs)
    try:
        pols = get_json(f'{b}/global/policies', h).get('policies') or []
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            return checks + [Check('Fleet: API token can read policies', False, 'Policies endpoint returned 401/403; '
                                   'firewall/screen lock/antivirus policy results unavailable.', ['endpoint', 'device'], 'Medium')]
        raise
    for sub, title, kw, sev in POLICY_KINDS:
        m = [p for p in pols if sub in (p.get('name') or '').lower()]
        if m:
            failing = sum(p.get('failing_host_count') or 0 for p in m)
            passing = sum(p.get('passing_host_count') or 0 for p in m)
            checks.append(Check(f'Fleet: {title}', failing == 0 and passing > 0,
                                f'{len(m)} matching polic(ies): {passing} passing / {failing} failing host result(s).', kw, sev))
    return checks


SPEC = {
    'key': 'fleet', 'name': 'Fleet', 'category': 'Endpoint Management', 'icon': 'fas fa-laptop', 'color': 'green',
    'capabilities': ['Disk encryption', 'OS version / check-in recency', 'Firewall / screen lock / antivirus via named policies'],
    'fields': [
        {'name': 'url', 'label': 'Fleet server URL (https only)', 'placeholder': 'https://fleet.example.com'},
        {'name': 'api_token', 'label': 'API-only user token', 'secret': True, 'placeholder': 'Fleet API token'}],
    'validate': validate, 'scan': scan,
}
