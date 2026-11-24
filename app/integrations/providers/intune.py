"""Microsoft Intune via Graph managedDevices. Client-credentials token from login.microsoftonline.com (tenant validated)."""
import re
from datetime import datetime, timedelta

import requests

from app.integrations import Check
from app.integrations.providers.kandji import _check, _ts, get_json

GRAPH, TIMEOUT, STALE_DAYS, MAX_PAGES = 'https://graph.microsoft.com/v1.0/deviceManagement/managedDevices', 20, 30, 50
KW = ['endpoint', 'device', 'encryption', 'mobile', 'compliance']
TENANT_RE = re.compile(r'[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}|[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}')


def _headers(cfg):
    t = (cfg.get('tenant_id') or '').strip()
    if not TENANT_RE.fullmatch(t):
        raise ValueError('invalid tenant id')
    r = requests.post(f'https://login.microsoftonline.com/{t}/oauth2/v2.0/token', timeout=TIMEOUT, allow_redirects=False,
                      data={'grant_type': 'client_credentials', 'client_id': cfg['client_id'], 'client_secret': cfg['client_secret'],
                            'scope': 'https://graph.microsoft.com/.default'})
    r.raise_for_status()
    return {'Authorization': f"Bearer {r.json()['access_token']}", 'Accept': 'application/json'}


def validate(cfg):
    get_json(GRAPH, _headers(cfg), params={'$top': 1})
    return cfg['tenant_id'].strip()


def scan(cfg):
    h, url, rows, params = _headers(cfg), GRAPH, [], {'$top': 100}
    try:
        for _ in range(MAX_PAGES):
            d = get_json(url, h, params=params)
            rows += d.get('value') or []
            url, params = d.get('@odata.nextLink'), None
            if not url or not url.startswith(GRAPH):  # never follow a link off the fixed Graph host
                break
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            return [Check('Intune: app can read managed devices', False, 'Graph returned 401/403. Grant DeviceManagementManagedDevices.Read.All.', KW, 'Medium')]
        raise
    cutoff = datetime.utcnow() - timedelta(days=STALE_DAYS)
    devs = [{'name': f"{x.get('deviceName') or x.get('id')} ({x.get('serialNumber') or '?'})", 'enc': x.get('isEncrypted'),
             'comp': x.get('complianceState'), 'seen': _ts((x.get('lastSyncDateTime') or '').rstrip('Z'))} for x in rows]
    known = [d for d in devs if d['enc'] is not None]
    out = [_check('Intune: disk encryption enabled on all managed devices', known, [d for d in known if not d['enc']], 'Unencrypted', KW, 'Critical')] if known else []
    return out + [
        _check('Intune: all managed devices compliant', devs, [d for d in devs if d['comp'] != 'compliant'], 'Non-compliant', KW, 'High'),
        _check(f'Intune: no stale devices (synced <{STALE_DAYS} days)', devs, [d for d in devs if d['seen'] is None or d['seen'] < cutoff], 'Stale', KW, 'Medium')]


SPEC = {
    'key': 'intune', 'name': 'Microsoft Intune', 'category': 'Endpoint Management', 'icon': 'fab fa-microsoft', 'color': 'blue',
    'capabilities': ['Disk encryption', 'Compliance state', 'Stale devices'],
    'fields': [{'name': 'tenant_id', 'label': 'Tenant ID', 'placeholder': 'GUID or contoso.onmicrosoft.com'},
               {'name': 'client_id', 'label': 'Application (client) ID', 'placeholder': 'App registration client ID'},
               {'name': 'client_secret', 'label': 'Client secret', 'secret': True, 'placeholder': 'App registration secret'}],
    'validate': validate, 'scan': scan,
}
