"""Google Cloud integration: service-account JWT-bearer OAuth2, read-only checks."""
import base64
import json
import re
import time
from datetime import datetime, timedelta, timezone

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.integrations import Check

TIMEOUT = 20
TOKEN_URL = 'https://oauth2.googleapis.com/token'  # fixed: never taken from the key file
SCOPE = 'https://www.googleapis.com/auth/cloud-platform.read-only'
KEY_MAX_AGE_DAYS = 90
PROJECT_RE = re.compile(r'^[a-z][a-z0-9-]{4,28}[a-z0-9]$')
MAX_PAGES = 20


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b'=')


def _token(cfg):
    try:
        sa = json.loads(cfg['service_account_json'])
        pk = serialization.load_pem_private_key(sa['private_key'].encode(), password=None)
        email = sa['client_email']
    except Exception:
        raise ValueError('service_account_json is not a valid service-account key')
    now = int(time.time())
    head = _b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode())
    body = _b64(json.dumps({'iss': email, 'scope': SCOPE, 'aud': TOKEN_URL, 'iat': now, 'exp': now + 3600}).encode())
    sig = pk.sign(head + b'.' + body, padding.PKCS1v15(), hashes.SHA256())
    r = requests.post(TOKEN_URL, timeout=TIMEOUT, allow_redirects=False, data={
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': (head + b'.' + body + b'.' + _b64(sig)).decode()})
    if r.status_code != 200:
        raise ValueError(f'Google rejected the service-account credentials (HTTP {r.status_code})')
    return r.json()['access_token']


def _project(cfg):
    pid = (cfg.get('project_id') or '').strip()
    if not PROJECT_RE.match(pid):
        raise ValueError('Invalid GCP project id')
    return pid


class _Api:
    def __init__(self, tok):
        self.h = {'Authorization': f'Bearer {tok}', 'Accept': 'application/json'}

    def call(self, method, url, **kw):
        r = requests.request(method, url, headers=self.h, timeout=TIMEOUT, allow_redirects=False, **kw)
        if r.status_code >= 400:
            raise PermissionError(f'HTTP {r.status_code}')
        return r.json()

    def pages(self, url, key, params=None):
        out, params = [], dict(params or {})
        for _ in range(MAX_PAGES):
            d = self.call('GET', url, params=params)
            out += d.get(key) or []
            if not d.get('nextPageToken'):
                break
            params['pageToken'] = d['nextPageToken']
        return out


def validate(cfg):
    pid = _project(cfg)
    r = requests.get(f'https://cloudresourcemanager.googleapis.com/v1/projects/{pid}',
                     headers={'Authorization': f'Bearer {_token(cfg)}'}, timeout=TIMEOUT, allow_redirects=False)
    if r.status_code != 200:
        raise ValueError(f'Cannot read project {pid} (HTTP {r.status_code}); check project id and roles')
    return r.json().get('name') or pid


def _ports_open(allowed, targets=('22', '3389')):
    for a in allowed:
        if (a.get('IPProtocol') or '').lower() not in ('tcp', 'all'):
            continue
        ports = a.get('ports')
        if not ports:
            return True
        for p in ports:
            lo, _, hi = p.partition('-')
            if lo.isdigit() and any(int(lo) <= int(t) <= int(hi or lo) for t in targets):
                return True
    return False


def _guard(title, kws, sev, perm, fn):
    try:
        ok, detail = fn()
        return Check(title, ok, detail, kws, sev)
    except Exception as e:  # a failing sub-call becomes a finding, not a crash
        return Check(title, False, f'Could not evaluate ({type(e).__name__}: {e}). '
                     f'Grant the service account {perm} on this project.', kws, sev)


def scan(cfg):
    pid = _project(cfg)
    try:
        api = _Api(_token(cfg))
    except Exception as e:
        raise ValueError(f'GCP authentication failed: {e}')
    cache = {}

    def buckets():
        if 'b' not in cache:
            cache['b'] = api.pages('https://storage.googleapis.com/storage/v1/b', 'items', {'project': pid})
        return cache['b']

    def sql():
        if 's' not in cache:
            cache['s'] = api.pages(f'https://sqladmin.googleapis.com/v1/projects/{pid}/instances', 'items')
        return cache['s']

    def public_buckets():
        bad = []
        for b in buckets():
            pol = api.call('GET', f'https://storage.googleapis.com/storage/v1/b/{b["name"]}/iam')
            if any(m in ('allUsers', 'allAuthenticatedUsers') for x in pol.get('bindings', []) for m in x.get('members', [])):
                bad.append(b['name'])
        return not bad, f'{len(buckets())} bucket(s) scanned. Public (allUsers/allAuthenticatedUsers): {", ".join(bad) or "none"}.'

    def ubla():
        bad = [b['name'] for b in buckets()
               if not ((b.get('iamConfiguration') or {}).get('uniformBucketLevelAccess') or {}).get('enabled')]
        return not bad, f'{len(buckets())} bucket(s) scanned. Uniform bucket-level access disabled on: {", ".join(bad) or "none"}.'

    def firewalls():
        fws = api.pages(f'https://compute.googleapis.com/compute/v1/projects/{pid}/global/firewalls', 'items')
        bad = [f['name'] for f in fws if f.get('direction', 'INGRESS') == 'INGRESS' and not f.get('disabled')
               and '0.0.0.0/0' in (f.get('sourceRanges') or []) and _ports_open(f.get('allowed') or [])]
        return not bad, f'{len(fws)} firewall rule(s) scanned. Open to 0.0.0.0/0 on 22/3389: {", ".join(bad) or "none"}.'

    def sa_keys():
        cutoff = datetime.now(timezone.utc) - timedelta(days=KEY_MAX_AGE_DAYS)
        accts = api.pages(f'https://iam.googleapis.com/v1/projects/{pid}/serviceAccounts', 'accounts')
        old = []
        for a in accts:
            keys = api.call('GET', f'https://iam.googleapis.com/v1/{a["name"]}/keys', params={'keyTypes': 'USER_MANAGED'})
            for k in keys.get('keys', []):
                if datetime.fromisoformat(k['validAfterTime'].replace('Z', '+00:00')) < cutoff:
                    old.append(a['email'])
        return not old, (f'{len(accts)} service account(s) scanned. User-managed keys older than {KEY_MAX_AGE_DAYS} days on: '
                         f'{", ".join(sorted(set(old))) or "none"}.')

    def sql_public():
        bad = [i['name'] for i in sql() if (i.get('settings', {}).get('ipConfiguration') or {}).get('ipv4Enabled')
               or any(n.get('value') == '0.0.0.0/0' for n in (i.get('settings', {}).get('ipConfiguration') or {}).get('authorizedNetworks', []))]
        return not bad, f'{len(sql())} Cloud SQL instance(s) scanned. Publicly reachable: {", ".join(bad) or "none"}.'

    def sql_ssl():
        def ok(i):
            ic = i.get('settings', {}).get('ipConfiguration') or {}
            return ic.get('requireSsl') or ic.get('sslMode') in ('ENCRYPTED_ONLY', 'TRUSTED_CLIENT_CERTIFICATE_REQUIRED')
        bad = [i['name'] for i in sql() if not ok(i)]
        return not bad, f'{len(sql())} Cloud SQL instance(s) scanned. SSL not required on: {", ".join(bad) or "none"}.'

    def audit():
        pol = api.call('POST', f'https://cloudresourcemanager.googleapis.com/v1/projects/{pid}:getIamPolicy', json={})
        types = {t['logType'] for c in pol.get('auditConfigs', []) if c.get('service') == 'allServices'
                 for t in c.get('auditLogConfigs', [])}
        missing = {'DATA_READ', 'DATA_WRITE'} - types
        return not missing, ('Data Access audit logs enabled for allServices.' if not missing
                             else f'Data Access audit logging not enabled for allServices: missing {", ".join(sorted(missing))}.')

    return [
        _guard('GCP: storage buckets are not publicly accessible', ['access control', 'data protection', 'public', 'cloud'],
               'Critical', 'roles/storage.admin read access (storage.buckets.list, storage.buckets.getIamPolicy)', public_buckets),
        _guard('GCP: storage buckets enforce uniform bucket-level access', ['access control', 'least privilege', 'cloud'],
               'Medium', 'storage.buckets.list', ubla),
        _guard('GCP: no firewall rule exposes SSH/RDP to the internet', ['network security', 'firewall', 'network', 'remote access'],
               'High', 'roles/compute.networkViewer (compute.firewalls.list)', firewalls),
        _guard(f'GCP: no user-managed service-account keys older than {KEY_MAX_AGE_DAYS} days',
               ['credential', 'key management', 'cryptograph', 'authentication', 'access control'],
               'High', 'roles/iam.serviceAccountViewer (iam.serviceAccounts.list, iam.serviceAccountKeys.list)', sa_keys),
        _guard('GCP: Cloud SQL instances have no public IP', ['database', 'network security', 'data protection', 'access control'],
               'High', 'roles/cloudsql.viewer (cloudsql.instances.list)', sql_public),
        _guard('GCP: Cloud SQL instances require SSL', ['encryption', 'in transit', 'cryptograph', 'database'],
               'Medium', 'roles/cloudsql.viewer (cloudsql.instances.list)', sql_ssl),
        _guard('GCP: Data Access audit logging is enabled', ['logging', 'audit', 'monitor', 'log'],
               'High', 'roles/browser or resourcemanager.projects.getIamPolicy', audit),
    ]


SPEC = {
    'key': 'gcp', 'name': 'Google Cloud', 'category': 'Cloud Providers', 'icon': 'fab fa-google', 'color': 'red',
    'capabilities': ['Public buckets and uniform access', 'Firewall exposure of SSH/RDP', 'Service-account key age',
                     'Cloud SQL public IP and SSL', 'Audit logging'],
    'fields': [
        {'name': 'service_account_json', 'label': 'Service account key (JSON)', 'secret': True,
         'placeholder': 'Paste a read-only service account JSON key'},
        {'name': 'project_id', 'label': 'Project ID', 'secret': False, 'placeholder': 'my-project-123'},
    ],
    'validate': validate, 'scan': scan,
}
