"""CrowdStrike Falcon EDR. OAuth2 client_credentials against the fixed api.crowdstrike.com host only."""
from datetime import datetime, timedelta

import requests

from app.integrations import Check
from app.integrations.providers.kandji import _check, _ts, truthy

BASE, TIMEOUT, STALE_DAYS, MAX_HOSTS = 'https://api.crowdstrike.com', 20, 30, 5000  # shortcut: first 5000 hosts, page for bigger fleets
KW = ['endpoint', 'device', 'malware', 'antivirus', 'edr']


def _token(cfg):
    r = requests.post(f'{BASE}/oauth2/token', data={'client_id': cfg['client_id'], 'client_secret': cfg['client_secret']},
                      timeout=TIMEOUT, allow_redirects=False)
    r.raise_for_status()
    return {'Authorization': f"Bearer {r.json()['access_token']}", 'Accept': 'application/json'}


def validate(cfg):
    h = _token(cfg)
    r = requests.get(f'{BASE}/devices/queries/devices/v1', headers=h, params={'limit': 1}, timeout=TIMEOUT, allow_redirects=False)
    r.raise_for_status()
    return 'CrowdStrike Falcon'


def scan(cfg):
    h = _token(cfg)
    try:
        r = requests.get(f'{BASE}/devices/queries/devices/v1', headers=h, params={'limit': MAX_HOSTS}, timeout=TIMEOUT, allow_redirects=False)
        r.raise_for_status()
        ids = r.json().get('resources') or []
        rows = []
        if ids:
            r = requests.post(f'{BASE}/devices/entities/devices/v2', headers=h, json={'ids': ids}, timeout=TIMEOUT, allow_redirects=False)
            r.raise_for_status()
            rows = r.json().get('resources') or []
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            return [Check('CrowdStrike: API client can read hosts', False, 'Hosts API returned 401/403. Grant the API client the Hosts: Read scope.', KW, 'Medium')]
        raise
    cutoff = datetime.utcnow() - timedelta(days=STALE_DAYS)
    devs = [{'name': f"{x.get('hostname') or x.get('device_id')} ({x.get('serial_number', '?')})", 'seen': _ts(x.get('last_seen')),
             'rfm': truthy(x.get('reduced_functionality_mode')),
             'pol': all((x.get('device_policies') or {}).get(k, {}).get('applied') for k in ('prevention', 'sensor_update'))} for x in rows]
    return [
        _check('CrowdStrike: sensor and prevention policy applied on all hosts', devs, [d for d in devs if not d['pol']], 'No policy applied', KW, 'High'),
        _check(f'CrowdStrike: no stale hosts (seen <{STALE_DAYS} days)', devs, [d for d in devs if d['seen'] is None or d['seen'] < cutoff], 'Stale', KW, 'Medium'),
        _check('CrowdStrike: no hosts in reduced functionality mode', devs, [d for d in devs if d['rfm']], 'Reduced functionality', KW, 'High')]


SPEC = {
    'key': 'crowdstrike', 'name': 'CrowdStrike Falcon', 'category': 'Endpoint Management', 'icon': 'fas fa-shield-virus', 'color': 'red',
    'capabilities': ['Sensor/prevention policy coverage', 'Stale hosts', 'Reduced functionality mode'],
    'fields': [{'name': 'client_id', 'label': 'API client ID', 'placeholder': 'Falcon API client ID'},
               {'name': 'client_secret', 'label': 'API client secret', 'secret': True, 'placeholder': 'Falcon API client secret'}],
    'validate': validate, 'scan': scan,
}
