"""Kandji MDM. Also hosts the helpers shared by jamf.py / fleet.py (providers must live in this package)."""
import re
from datetime import datetime, timedelta

import requests

from app.integrations import Check

TIMEOUT, STALE_DAYS, MAX_PAGES, MAX_DETAIL = 20, 30, 50, 500
APPLE = ('darwin', 'mac', 'ios', 'ipad', 'iphone', 'tvos', 'visionos')
HOSTS = ('api.kandji.io', 'api.eu.kandji.io')


def get_json(url, headers, **kw):
    r = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=False, **kw)
    r.raise_for_status()
    return r.json()


def truthy(v):
    """True/False/None(unknown) from the bool-or-string flags MDM APIs return."""
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower() if v is not None else ''
    return True if s in ('yes', 'true', 'enabled', 'on', 'encrypted') else False if s in ('no', 'false', 'disabled', 'off', 'decrypted', 'not encrypted') else None


def _ts(s):
    try:
        return datetime.fromisoformat(str(s)[:19])
    except ValueError:
        return None


def _major(v):
    m = re.search(r'\d+', v or '')
    return int(m.group()) if m else None


def _check(title, devs, bad, noun, kw, sev):
    names = [d['name'] for d in bad]
    detail = f'{len(devs)} device(s) evaluated. {noun}: {len(bad)}'
    if bad:
        detail += f' ({", ".join(names[:10])}{"..." if len(names) > 10 else ""})'
    return Check(title, not bad, detail + '.', kw, sev)


def mdm_checks(prefix, devs):
    """devs: dicts {name, platform, os, seen, enc, fw} (enc/fw True/False/None=API does not say). Emits no check for a
    signal no device reports. Names are 'hostname (serial)'; no secrets ever enter here."""
    out = []
    for key, title, noun, kw, sev in (
            ('enc', 'disk encryption enabled on all managed devices (FileVault/BitLocker)', 'Unencrypted',
             ['encryption', 'endpoint', 'device', 'cryptograph', 'mobile', 'data protection'], 'Critical'),
            ('fw', 'host firewall enabled on all managed devices', 'Firewall off',
             ['firewall', 'endpoint', 'device', 'network security'], 'Medium')):
        known = [d for d in devs if d.get(key) is not None]
        if known:
            out.append(_check(f'{prefix}: {title}', known, [d for d in known if not d[key]], noun, kw, sev))
    if devs:
        cutoff = datetime.utcnow() - timedelta(days=STALE_DAYS)
        newest = {}
        for d in devs:
            p = (d.get('platform') or '').lower()
            if any(a in p for a in APPLE) and _major(d.get('os')):
                newest[p] = max(newest.get(p, 0), _major(d['os']))

        def old(d):
            p, seen, mj = (d.get('platform') or '').lower(), _ts(d.get('seen')), _major(d.get('os'))
            return (seen is None or seen < cutoff) or (p in newest and mj is not None and mj < newest[p] - 1)
        out.append(_check(f'{prefix}: OS current (within N-1 major) and checking in (<{STALE_DAYS} days)', devs,
                          [d for d in devs if old(d)], 'Outdated OS or no recent check-in',
                          ['patch', 'vulnerab', 'endpoint', 'device', 'software update', 'malware'], 'High'))
    return out


def _sub(cfg, suffix):
    sub = (cfg.get('subdomain') or '').strip().lower()
    if not re.fullmatch(r'[a-z0-9-]+', sub) or sub.startswith('-'):
        raise ValueError('invalid subdomain')
    return f'{sub}.{suffix}'


def host(cfg):
    rh = (cfg.get('region_host') or '').strip().lower()
    if rh not in HOSTS:
        raise ValueError('region_host must be api.kandji.io or api.eu.kandji.io')
    return _sub(cfg, rh)


def _headers(cfg):
    return {'Authorization': f"Bearer {cfg['api_token']}", 'Accept': 'application/json'}


def _devices(cfg):
    base, out = f'https://{host(cfg)}/api/v1/devices', []
    for page in range(MAX_PAGES):
        rows = get_json(base, _headers(cfg), params={'limit': 300, 'offset': page * 300})
        out += rows
        if len(rows) < 300:
            break
    return out


def validate(cfg):
    get_json(f'https://{host(cfg)}/api/v1/devices', _headers(cfg), params={'limit': 1})
    return cfg['subdomain']


def scan(cfg):
    base, h, rows = f'https://{host(cfg)}/api/v1/devices', _headers(cfg), _devices(cfg)
    devs, denied = [], False
    for i, r in enumerate(rows):
        d = {'name': f"{r.get('device_name') or r.get('device_id')} ({r.get('serial_number', '?')})",
             'platform': r.get('platform'), 'os': r.get('os_version'), 'seen': r.get('last_check_in')}
        if i < MAX_DETAIL and not denied:  # shortcut: detail call per device, capped; raise cap/parallelise for big fleets
            try:
                det = get_json(f"{base}/{r['device_id']}/details", h)
                d['enc'] = truthy((det.get('filevault') or {}).get('filevault_enabled'))
                d['fw'] = truthy((det.get('security_information') or {}).get('firewall_enabled'))
            except requests.HTTPError as e:
                denied = denied or e.response is not None and e.response.status_code in (401, 403)
            except (requests.RequestException, ValueError, KeyError):
                pass
        devs.append(d)
    checks = mdm_checks('Kandji', devs)
    if denied:
        checks.append(Check('Kandji: API token can read device details', False,
                            'Device detail endpoint returned 401/403; encryption and firewall could not be evaluated. '
                            'Grant the token the device-information read permission.', ['endpoint', 'device'], 'Medium'))
    return checks


SPEC = {
    'key': 'kandji', 'name': 'Kandji', 'category': 'Endpoint Management', 'icon': 'fas fa-laptop', 'color': 'blue',
    'capabilities': ['Disk encryption (FileVault)', 'Firewall', 'OS version / check-in recency'],
    'fields': [
        {'name': 'subdomain', 'label': 'Kandji subdomain', 'placeholder': 'acme'},
        {'name': 'region_host', 'label': 'API host', 'placeholder': 'api.kandji.io or api.eu.kandji.io'},
        {'name': 'api_token', 'label': 'API token', 'secret': True, 'placeholder': 'Kandji API token'}],
    'validate': validate, 'scan': scan,
}
