"""DigitalOcean integration: read-only API token, fixed vendor host."""
import requests

from app.integrations import Check

TIMEOUT = 20
API = 'https://api.digitalocean.com'
MAX_PAGES = 20


class _Api:
    def __init__(self, token):
        self.h = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}

    def get(self, path, **params):
        r = requests.get(f'{API}{path}', headers=self.h, params=params, timeout=TIMEOUT, allow_redirects=False)
        if r.status_code >= 400:
            raise PermissionError(f'HTTP {r.status_code}')
        return r.json()

    def all(self, path, key):  # pages via ?page=N so the host can never be redirected by the response
        out = []
        for n in range(1, MAX_PAGES + 1):
            d = self.get(path, page=n, per_page=200)
            out += d.get(key) or []
            if not ((d.get('links') or {}).get('pages') or {}).get('next'):
                break
        return out


def validate(cfg):
    r = requests.get(f'{API}/v2/account', headers={'Authorization': f'Bearer {cfg["api_token"]}'},
                     timeout=TIMEOUT, allow_redirects=False)
    if r.status_code != 200:
        raise ValueError(f'DigitalOcean rejected the token (HTTP {r.status_code})')
    a = r.json().get('account') or {}
    return (a.get('team') or {}).get('name') or (a.get('uuid') or 'account')[:8]


def _open_admin(fw):
    for rule in fw.get('inbound_rules') or []:
        if '0.0.0.0/0' not in (rule.get('sources') or {}).get('addresses', []):
            continue
        if rule.get('protocol') != 'tcp':
            continue
        ports = str(rule.get('ports', '0'))
        if ports in ('0', 'all'):
            return True
        lo, _, hi = ports.partition('-')
        if lo.isdigit() and any(int(lo) <= t <= int(hi or lo) for t in (22, 3389)):
            return True
    return False


def _guard(title, kws, sev, perm, fn):
    try:
        ok, detail = fn()
        return Check(title, ok, detail, kws, sev)
    except Exception as e:  # a failing sub-call becomes a finding, not a crash
        return Check(title, False, f'Could not evaluate ({type(e).__name__}: {e}). Token needs {perm}.', kws, sev)


def scan(cfg):
    api = _Api(cfg['api_token'])
    cache = {}

    def get(name, path, key):
        if name not in cache:
            cache[name] = api.all(path, key)
        return cache[name]

    def firewalls():
        fws = get('fw', '/v2/firewalls', 'firewalls')
        bad = [f['name'] for f in fws if _open_admin(f)]
        return not bad, f'{len(fws)} firewall(s) scanned. Open to 0.0.0.0/0 on 22/3389: {", ".join(bad) or "none"}.'

    def unfirewalled():
        fws, ds = get('fw', '/v2/firewalls', 'firewalls'), get('dr', '/v2/droplets', 'droplets')
        ids = {i for f in fws for i in f.get('droplet_ids') or []}
        tags = {t for f in fws for t in f.get('tags') or []}
        bad = [d['name'] for d in ds if d['id'] not in ids and not tags & set(d.get('tags') or [])]
        return not bad, f'{len(ds)} droplet(s) scanned. Without any firewall: {", ".join(bad) or "none"}.'

    def backups():
        ds = get('dr', '/v2/droplets', 'droplets')
        bad = [d['name'] for d in ds if 'backups' not in (d.get('features') or [])]
        return not bad, f'{len(ds)} droplet(s) scanned. Backups disabled on: {", ".join(bad) or "none"}.'

    def dbs():
        cl = get('db', '/v2/databases', 'databases')
        bad = []
        for c in cl:
            rules = api.get(f'/v2/databases/{c["id"]}/firewall').get('rules') or []
            if not rules or any(r.get('type') == 'ip_addr' and r.get('value') in ('0.0.0.0/0', '::/0') for r in rules):
                bad.append(c['name'])
        return not bad, f'{len(cl)} database cluster(s) scanned. Trusted sources unrestricted on: {", ".join(bad) or "none"}.'

    checks = [
        _guard('DigitalOcean: no firewall exposes SSH/RDP to the internet', ['network security', 'firewall', 'network', 'remote access'],
               'High', 'read scope for firewalls', firewalls),
        _guard('DigitalOcean: droplets are protected by a firewall', ['network security', 'firewall', 'network', 'segmentation'],
               'High', 'read scope for droplets and firewalls', unfirewalled),
        _guard('DigitalOcean: droplet backups are enabled', ['backup', 'recovery', 'continuity', 'availability'],
               'Medium', 'read scope for droplets', backups),
        _guard('DigitalOcean: managed databases restrict trusted sources', ['database', 'access control', 'network security', 'data protection'],
               'High', 'read scope for databases', dbs),
    ]
    # shortcut: DO's public API exposes no 2FA flag on most accounts; check only when the field is present
    try:
        a = api.get('/v2/account').get('account') or {}
        flag = a.get('two_factor_enabled', (a.get('team') or {}).get('two_factor_required'))
        if flag is not None:
            checks.append(Check('DigitalOcean: two-factor authentication is enforced', bool(flag),
                                '2FA is enforced on the account.' if flag else '2FA is not enforced on the account.',
                                ['multi-factor', 'mfa', 'authentication'], 'High'))
    except Exception:
        pass
    return checks


SPEC = {
    'key': 'digitalocean', 'name': 'DigitalOcean', 'category': 'Cloud Providers', 'icon': 'fab fa-digital-ocean',
    'color': 'blue',
    'capabilities': ['Firewall exposure of SSH/RDP', 'Droplet firewall coverage', 'Droplet backups',
                     'Database trusted sources', '2FA enforcement (when exposed)'],
    'fields': [{'name': 'api_token', 'label': 'API token (read-only)', 'secret': True, 'placeholder': 'dop_v1_...'}],
    'validate': validate, 'scan': scan,
}
