"""Tests for the auth0 / jumpcloud / bamboohr / cloudflare providers (requests mocked)."""
from datetime import date, timedelta
from unittest import mock

import pytest
import requests

from app.integrations import registry
from app.integrations.providers import auth0, bamboohr, cloudflare, jumpcloud


class Resp:
    def __init__(self, data=None, code=200):
        self.data, self.status_code, self.links = data, code, {}

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


def router(mod, routes):
    """Patch mod.requests.request; routes = {url-substring: data | (data, code)}; longest match wins."""
    calls = []

    def fake(method, url, **kw):
        calls.append((method, url, kw))
        for k in sorted(routes, key=len, reverse=True):
            if k in url:
                v = routes[k]
                return Resp(*v) if isinstance(v, tuple) else Resp(v)
        return Resp({}, 404)
    p = mock.patch.object(mod.requests, 'request', side_effect=fake)
    p.start()
    return calls, p


@pytest.fixture(autouse=True)
def _stop():
    yield
    mock.patch.stopall()


def by_title(checks):
    return {c.title: c for c in checks}


def test_registry_discovers_all():
    r = registry()
    assert {'auth0', 'jumpcloud', 'bamboohr', 'cloudflare'} <= set(r)
    assert r['auth0']['category'] == r['jumpcloud']['category'] == 'Identity Providers'
    assert r['bamboohr']['category'] == 'HR Systems' and r['cloudflare']['category'] == 'SaaS Application'


# ---- Auth0
A0 = {'domain': 'acme.us.auth0.com', 'client_id': 'id', 'client_secret': 'SECRET'}


def a0_routes(**over):
    r = {'/oauth/token': {'access_token': 'TOK'},
         '/guardian/factors': [{'name': 'otp', 'enabled': True}, {'name': 'sms', 'enabled': False}],
         '/brute-force-protection': {'enabled': True}, '/breached-password-detection': {'enabled': True},
         '/connections': [{'name': 'db', 'options': {'passwordPolicy': 'good'}}],
         '/log-streams': [{'status': 'active'}]}
    r.update(over)
    return r


def test_auth0_all_pass_and_secret_free():
    router(auth0, a0_routes())
    cs = auth0.scan(A0)
    assert len(cs) == 5 and all(c.passed for c in cs)
    assert all('SECRET' not in c.detail and 'TOK' not in c.detail for c in cs)


def test_auth0_failures():
    router(auth0, a0_routes(**{'/guardian/factors': [{'name': 'otp', 'enabled': False}],
                               '/brute-force-protection': {'enabled': False},
                               '/connections': [{'name': 'db', 'options': {'passwordPolicy': 'low'}}],
                               '/log-streams': []}))
    t = by_title(auth0.scan(A0))
    assert not t['Auth0: MFA factors enabled'].passed
    assert not t['Auth0: brute-force protection enabled'].passed
    assert t['Auth0: breached-password detection enabled'].passed
    assert not t['Auth0: database connection password policy >= good'].passed
    assert not t['Auth0: tenant log streaming configured'].passed


def test_auth0_403_does_not_crash():
    router(auth0, a0_routes(**{'/guardian/factors': ({}, 403)}))
    t = by_title(auth0.scan(A0))
    c = t['Auth0: MFA factors enabled']
    assert not c.passed and '403' in c.detail
    assert t['Auth0: brute-force protection enabled'].passed


@pytest.mark.parametrize('d', ['evil.com', 'acme.auth0.com.evil.com', 'acme.us.auth0.com/x', 'x@acme.auth0.com', ''])
def test_auth0_host_rejected(d):
    calls, _ = router(auth0, a0_routes())
    with pytest.raises(ValueError):
        auth0.validate({**A0, 'domain': d})
    assert not calls
    assert not auth0.scan({**A0, 'domain': d})[0].passed
    assert not calls


# ---- JumpCloud
JC = {'api_key': 'SECRET'}


def jc_routes(**over):
    r = {'/api/systemusers': {'results': [
            {'_id': 'u1', 'username': 'a', 'mfa': {'configured': True}},
            {'_id': 'u2', 'username': 'b', 'suspended': True, 'state': 'SUSPENDED'}]},
         '/api/systems': {'results': [{'_id': 's1', 'hostname': 'h1', 'fde': {'active': True}}]},
         '/api/v2/usergroups/g1/members': [{'to': {'id': 'u1'}}],
         '/api/v2/usergroups': [{'id': 'g1'}]}
    r.update(over)
    return r


def test_jumpcloud_pass():
    router(jumpcloud, jc_routes())
    assert all(c.passed for c in jumpcloud.scan(JC))


def test_jumpcloud_fail():
    router(jumpcloud, jc_routes(**{
        '/api/systemusers': {'results': [{'_id': 'u1', 'username': 'a', 'password_never_expires': True},
                                         {'_id': 'u2', 'username': 'b', 'suspended': True}]},
        '/api/systems': {'results': [{'_id': 's1', 'hostname': 'h1', 'fde': {'active': False}}]},
        '/api/v2/usergroups/g1/members': [{'to': {'id': 'u2'}}]}))
    t = by_title(jumpcloud.scan(JC))
    assert not any(c.passed for c in t.values())
    assert 'h1' in t['JumpCloud: systems have disk encryption'].detail


def test_jumpcloud_403_and_host():
    router(jumpcloud, jc_routes(**{'/api/systems': ({}, 403)}))
    t = by_title(jumpcloud.scan(JC))
    assert '403' in t['JumpCloud: systems have disk encryption'].detail
    assert t['JumpCloud: all active users enrolled in MFA'].passed
    calls, _ = router(jumpcloud, jc_routes())
    assert jumpcloud.validate({**JC, 'host': 'console.eu.jumpcloud.com'}) == 'console.eu.jumpcloud.com'
    with pytest.raises(ValueError):
        jumpcloud.validate({**JC, 'host': 'console.jumpcloud.com.evil.com'})
    assert not any('evil' in c[1] for c in calls)


# ---- BambooHR
BH = {'subdomain': 'acme', 'api_key': 'SECRET'}
RECENT = (date.today() - timedelta(days=5)).isoformat()


def test_bamboohr_checks():
    emps = [{'id': '1', 'status': 'Active', 'hireDate': '2020-01-01', 'supervisorEId': '9'},
            {'id': '2', 'status': 'Active', 'hireDate': '', 'supervisorEId': '9'},
            {'id': '3', 'status': 'Inactive', 'terminationDate': RECENT},
            {'id': '4', 'status': 'Inactive', 'terminationDate': '2001-01-01'}]
    calls, _ = router(bamboohr, {'/reports/custom': {'employees': emps}})
    t = by_title(bamboohr.scan(BH))
    assert 'api.bamboohr.com/api/gateway.php/acme/' in calls[0][1]
    assert '1 employee(s) terminated' in t['BambooHR: recent terminations recorded'].detail
    assert 'ids: 3' in t['BambooHR: recent terminations recorded'].detail
    assert not t['BambooHR: active employee records complete'].passed
    assert '2 active' in t['BambooHR: headcount snapshot'].detail
    good = [e for e in emps if e['id'] == '1']
    router(bamboohr, {'/reports/custom': {'employees': good}})
    assert all(c.passed for c in bamboohr.scan(BH))


def test_bamboohr_403_and_host():
    router(bamboohr, {'/reports/custom': ({}, 403)})
    cs = bamboohr.scan(BH)
    assert len(cs) == 3 and not any(c.passed for c in cs) and '403' in cs[0].detail
    calls, _ = router(bamboohr, {})
    for s in ('evil.com/x', 'a.b', 'a/../b', ''):
        with pytest.raises(ValueError):
            bamboohr.validate({**BH, 'subdomain': s})
    assert not calls


# ---- Cloudflare
CF = {'api_token': 'SECRET'}
GOOD_SETTINGS = [{'id': 'ssl', 'value': 'strict'}, {'id': 'always_use_https', 'value': 'on'},
                 {'id': 'min_tls_version', 'value': '1.2'},
                 {'id': 'security_header', 'value': {'strict_transport_security': {'enabled': True}}}]


def cf_routes(**over):
    r = {'/zones/z1/settings': {'result': GOOD_SETTINGS},
         '/zones/z1/dnssec': {'result': {'status': 'active'}},
         '/zones/z1/rulesets/phases': {'result': {'rules': [{'enabled': True}]}},
         '/client/v4/zones': {'result': [{'id': 'z1', 'name': 'example.com'}], 'result_info': {'total_pages': 1}}}
    r.update(over)
    return r


def test_cloudflare_pass():
    router(cloudflare, cf_routes())
    cs = cloudflare.scan(CF)
    assert len(cs) == 6 and all(c.passed for c in cs)


def test_cloudflare_fail():
    bad = [{'id': 'ssl', 'value': 'flexible'}, {'id': 'always_use_https', 'value': 'off'},
           {'id': 'min_tls_version', 'value': '1.0'}, {'id': 'security_header', 'value': {}}]
    router(cloudflare, cf_routes(**{'/zones/z1/settings': {'result': bad},
                                    '/zones/z1/dnssec': {'result': {'status': 'disabled'}},
                                    '/zones/z1/rulesets/phases': ({}, 404)}))
    cs = cloudflare.scan(CF)
    assert not any(c.passed for c in cs) and all('example.com' in c.detail for c in cs)


def test_cloudflare_403_paths():
    router(cloudflare, cf_routes(**{'/zones/z1/dnssec': ({}, 403)}))
    t = by_title(cloudflare.scan(CF))
    assert '403' in t['Cloudflare: DNSSEC enabled'].detail and t['Cloudflare: HSTS enabled'].passed
    router(cloudflare, cf_routes(**{'/client/v4/zones': ({}, 403)}))
    cs = cloudflare.scan(CF)
    assert len(cs) == 1 and not cs[0].passed


def test_cloudflare_only_cloudflare_host():
    calls, _ = router(cloudflare, cf_routes(**{'/user/tokens/verify': {'result': {'status': 'active'}}}))
    cloudflare.validate(CF)
    cloudflare.scan(CF)
    assert all(c[1].startswith('https://api.cloudflare.com/client/v4/') for c in calls)
