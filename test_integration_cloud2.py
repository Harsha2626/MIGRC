import json
import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.integrations import registry
from app.integrations.providers import gcp, digitalocean as do


class Resp:
    def __init__(self, data, code=200):
        self.data, self.status_code = data, code

    def json(self):
        return self.data


def install(monkeypatch, routes, calls=None):
    """routes: list of (substring, data|code int); first match wins; unmatched -> 403."""
    def fake(method, url, **kw):
        if calls is not None:
            calls.append((method, url))
        assert url.startswith(('https://oauth2.googleapis.com/', 'https://api.digitalocean.com/')) or '.googleapis.com/' in url
        for sub, data in routes:
            if sub in url:
                return Resp({}, data) if isinstance(data, int) else Resp(data)
        return Resp({}, 403)
    monkeypatch.setattr(requests, 'request', fake)
    monkeypatch.setattr(requests, 'get', lambda url, **kw: fake('GET', url, **kw))
    monkeypatch.setattr(requests, 'post', lambda url, **kw: fake('POST', url, **kw))


def by_title(checks):
    return {c.title: c for c in checks}


def test_registry_discovers_both():
    r = registry()
    assert r['gcp']['name'] == 'Google Cloud' and r['digitalocean']['category'] == 'Cloud Providers'
    assert r['gcp']['fields'][0]['secret'] and r['digitalocean']['fields'][0]['secret']


# ---- GCP ----
PEM = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
CFG = {'service_account_json': json.dumps({'client_email': 'sa@p.iam.gserviceaccount.com', 'private_key': PEM}),
       'project_id': 'my-proj-123'}
TOK = ('oauth2.googleapis.com/token', {'access_token': 't'})


def gcp_routes(bad):
    return [TOK,
            ('/storage/v1/b/pub/iam', {'bindings': [{'members': ['allUsers']}]}),
            ('/storage/v1/b/priv/iam', {'bindings': [{'members': ['user:a@b.c']}]}),
            ('/storage/v1/b', {'items': [{'name': 'pub' if bad else 'priv',
                                           'iamConfiguration': {'uniformBucketLevelAccess': {'enabled': not bad}}}]}),
            ('compute/v1', {'items': [{'name': 'fw', 'direction': 'INGRESS', 'sourceRanges': ['0.0.0.0/0'],
                                       'allowed': [{'IPProtocol': 'tcp', 'ports': ['20-25' if bad else '443']}]}]}),
            ('serviceAccounts/', {'keys': [{'validAfterTime': '2020-01-01T00:00:00Z' if bad else '2999-01-01T00:00:00Z'}]}),
            ('/serviceAccounts', {'accounts': [{'name': 'projects/p/serviceAccounts/sa', 'email': 'sa@x'}]}),
            ('sqladmin', {'items': [{'name': 'db', 'settings': {'ipConfiguration': (
                {'ipv4Enabled': True} if bad else {'ipv4Enabled': False, 'sslMode': 'ENCRYPTED_ONLY'})}}]}),
            (':getIamPolicy', {} if bad else {'auditConfigs': [{'service': 'allServices', 'auditLogConfigs': [
                {'logType': 'DATA_READ'}, {'logType': 'DATA_WRITE'}]}]})]


@pytest.mark.parametrize('bad', [False, True])
def test_gcp_pass_fail(monkeypatch, bad):
    install(monkeypatch, gcp_routes(bad))
    cs = gcp.scan(CFG)
    assert len(cs) == 7 and all(c.title.startswith('GCP: ') for c in cs)
    assert all(c.passed != bad for c in cs), [(c.title, c.detail) for c in cs]
    assert not any('Could not evaluate' in c.detail for c in cs)
    assert 'BEGIN' not in ''.join(c.detail for c in cs)


def test_gcp_permission_denied_does_not_crash(monkeypatch):
    install(monkeypatch, [TOK])  # everything else 403
    cs = gcp.scan(CFG)
    assert len(cs) == 7 and not any(c.passed for c in cs)
    assert all('Could not evaluate' in c.detail for c in cs)


def test_gcp_validate_and_hosts(monkeypatch):
    calls = []
    install(monkeypatch, [TOK, ('cloudresourcemanager', {'name': 'My Project'})], calls)
    assert gcp.validate(CFG) == 'My Project'
    assert calls[0][1] == 'https://oauth2.googleapis.com/token'
    install(monkeypatch, [TOK, ('cloudresourcemanager', 403)])
    with pytest.raises(ValueError):
        gcp.validate(CFG)
    with pytest.raises(ValueError):
        gcp.validate({**CFG, 'project_id': '../evil'})


# ---- DigitalOcean ----
DOCFG = {'api_token': 'tok'}


def do_routes(bad, twofa=None):
    acct = {'uuid': 'abcdef123456', 'team': {'name': 'Acme'}}
    if twofa is not None:
        acct['two_factor_enabled'] = twofa
    return [('/v2/account', {'account': acct}),
            ('/v2/firewalls', {'firewalls': [{'name': 'fw', 'droplet_ids': [] if bad else [1],
                                              'inbound_rules': [{'protocol': 'tcp', 'ports': '22' if bad else '443',
                                                                 'sources': {'addresses': ['0.0.0.0/0']}}]}]}),
            ('/v2/droplets', {'droplets': [{'id': 1, 'name': 'd', 'features': [] if bad else ['backups']}]}),
            ('/firewall', {'rules': [] if bad else [{'type': 'ip_addr', 'value': '10.0.0.1'}]}),
            ('/v2/databases', {'databases': [{'id': 'x', 'name': 'pg'}]})]


@pytest.mark.parametrize('bad', [False, True])
def test_do_pass_fail(monkeypatch, bad):
    install(monkeypatch, do_routes(bad, twofa=not bad))
    cs = do.scan(DOCFG)
    assert len(cs) == 5 and all(c.title.startswith('DigitalOcean: ') for c in cs)
    assert all(c.passed != bad for c in cs), [(c.title, c.detail) for c in cs]
    assert not any('Could not evaluate' in c.detail for c in cs)


def test_do_2fa_skipped_when_not_exposed(monkeypatch):
    install(monkeypatch, do_routes(False))
    assert len(do.scan(DOCFG)) == 4


def test_do_permission_denied(monkeypatch):
    install(monkeypatch, [])
    cs = do.scan(DOCFG)
    assert len(cs) == 4 and not any(c.passed for c in cs)
    assert all('Could not evaluate' in c.detail for c in cs)


def test_do_validate(monkeypatch):
    install(monkeypatch, do_routes(False))
    assert do.validate(DOCFG) == 'Acme'
    install(monkeypatch, [])
    with pytest.raises(ValueError):
        do.validate(DOCFG)
