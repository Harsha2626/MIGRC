"""Jamf Pro (OAuth client credentials, Jamf Cloud hosts only)."""
import requests

from app.integrations import Check
from app.integrations.providers.kandji import MAX_PAGES, TIMEOUT, _sub, get_json, mdm_checks, truthy

SECTIONS = ['GENERAL', 'HARDWARE', 'OPERATING_SYSTEM', 'DISK_ENCRYPTION', 'SECURITY']


def host(cfg):
    return _sub(cfg, 'jamfcloud.com')


def _token(cfg):
    r = requests.post(f'https://{host(cfg)}/api/oauth/token', timeout=TIMEOUT, allow_redirects=False,
                      data={'grant_type': 'client_credentials', 'client_id': cfg['client_id'],
                            'client_secret': cfg['client_secret']})
    r.raise_for_status()
    return r.json()['access_token']


def _h(cfg):
    return {'Authorization': f'Bearer {_token(cfg)}', 'Accept': 'application/json'}


def validate(cfg):
    get_json(f'https://{host(cfg)}/api/v1/computers-inventory', _h(cfg), params={'page-size': 1, 'section': 'GENERAL'})
    return cfg['subdomain']


def scan(cfg):
    h, url, rows = _h(cfg), f'https://{host(cfg)}/api/v1/computers-inventory', []
    try:
        for page in range(MAX_PAGES):
            d = get_json(url, h, params={'section': SECTIONS, 'page': page, 'page-size': 100})
            rows += d.get('results') or []
            if len(rows) >= d.get('totalCount', 0) or not d.get('results'):
                break
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            return [Check('Jamf: API client can read computer inventory', False,
                          'Inventory endpoint returned 401/403. Grant the API role "Read Computer Inventory Collection".',
                          ['endpoint', 'device'], 'Medium')]
        raise
    devs = []
    for r in rows:
        g, sec = r.get('general') or {}, r.get('security') or {}
        enc = ((r.get('diskEncryption') or {}).get('bootPartitionEncryptionDetails') or {}).get('partitionFileVault2State')
        devs.append({'name': f"{g.get('name') or r.get('id')} ({(r.get('hardware') or {}).get('serialNumber', '?')})",
                     'platform': 'macOS', 'os': (r.get('operatingSystem') or {}).get('version'),
                     'seen': g.get('lastContactTime'),
                     'enc': None if not enc else str(enc).upper() == 'ENCRYPTED', 'fw': truthy(sec.get('firewallEnabled'))})
    return mdm_checks('Jamf', devs)


SPEC = {
    'key': 'jamf', 'name': 'Jamf Pro', 'category': 'Endpoint Management', 'icon': 'fas fa-laptop', 'color': 'orange',
    'capabilities': ['Disk encryption (FileVault)', 'Firewall', 'OS version / check-in recency'],
    'fields': [
        {'name': 'subdomain', 'label': 'Jamf Cloud subdomain (<name>.jamfcloud.com)', 'placeholder': 'acme'},
        {'name': 'client_id', 'label': 'API client ID', 'placeholder': 'API client ID'},
        {'name': 'client_secret', 'label': 'API client secret', 'secret': True, 'placeholder': 'API client secret'}],
    'validate': validate, 'scan': scan,
}
