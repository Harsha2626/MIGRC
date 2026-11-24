"""Tests for gusto / rippling / onepassword providers (requests mocked)."""
from datetime import date, timedelta

import pytest
from unittest import mock

from app.integrations import registry
from app.integrations.providers import gusto, onepassword, rippling
from test_integration_identity import router, by_title, Resp  # noqa: F401


@pytest.fixture(autouse=True)
def _stop():
    yield
    mock.patch.stopall()


NOW = date.today().isoformat()
OLD = (date.today() - timedelta(days=200)).isoformat()
G = {'company_id': 'abc-123-def-456', 'token': 'SECRET'}
R = {'token': 'SECRET'}
O = {'token': 'SECRET'}


def test_registry():
    r = registry()
    assert r['gusto']['category'] == r['rippling']['category'] == 'HR Systems'
    assert r['onepassword']['category'] == 'Identity Providers'


def test_gusto_pass_fail_403():
    def run(act, term):
        def fake(method, url, **kw):
            assert url.startswith('https://api.gusto.com/') and kw['allow_redirects'] is False
            return Resp(term if kw['params']['terminated'] == 'true' else act)
        mock.patch.object(gusto.requests, 'request', side_effect=fake).start()
        return gusto.scan(G)
    good = [{'uuid': 'u1', 'onboarded': True, 'jobs': [{'hire_date': OLD}]}]
    cs = run(good, [{'uuid': 'u2', 'terminations': [{'effective_date': NOW}]}])
    assert all(c.passed for c in cs) and '(ids: u2)' in cs[0].detail
    assert all('SECRET' not in c.detail for c in cs)
    cs = run([{'uuid': 'u1', 'onboarded': False, 'jobs': []}], [])
    assert not cs[1].passed and '(ids: u1)' in cs[1].detail
    mock.patch.stopall()
    router(gusto, {'/employees': ({}, 403)})
    cs = gusto.scan(G)
    assert len(cs) == 3 and not any(c.passed for c in cs) and all(c.severity == 'Low' for c in cs)
    assert '403' in cs[0].detail


def test_rippling_pass_fail_403():
    calls, _ = router(rippling, {'/employees/include_terminated': [
        {'id': 'a', 'roleState': 'ACTIVE', 'startDate': OLD},
        {'id': 'b', 'roleState': 'TERMINATED', 'endDate': NOW + 'T00:00:00Z'}]})
    cs = rippling.scan(R)
    assert all(c.passed for c in cs) and '(ids: b)' in cs[0].detail
    assert calls[0][1].startswith('https://api.rippling.com/') and calls[0][2]['allow_redirects'] is False
    mock.patch.stopall()
    router(rippling, {'/employees': [{'id': 'a', 'roleState': 'ACTIVE'}]})
    assert not by_title(rippling.scan(R))['Rippling: active employee records complete'].passed
    mock.patch.stopall()
    router(rippling, {'/employees': ({}, 401)})
    cs = rippling.scan(R)
    assert not any(c.passed for c in cs) and all(c.severity == 'Low' for c in cs)


def test_onepassword_pass_fail_403():
    ok = {'/signinattempts': {'items': [{'category': 'success'}]},
          '/auditevents': {'items': [{'action': 'create', 'object_type': 'item'}]},
          '/itemusages': {'items': [{'action': 'reveal'}]}}
    calls, _ = router(onepassword, ok)
    cs = onepassword.scan(O)
    assert len(cs) == 3 and all(c.passed for c in cs)
    assert all(c[1].startswith('https://events.1password.com/') and c[2]['allow_redirects'] is False for c in calls)
    assert all('SECRET' not in c.detail for c in cs)
    mock.patch.stopall()
    router(onepassword, {'/signinattempts': {'items': [{'category': 'credentials_failed'}] * 25},
                         '/auditevents': {'items': [{'action': 'disable', 'object_type': 'mfa'}]},
                         '/itemusages': {'items': [{'action': 'share'}] * 30}})
    assert not any(c.passed for c in onepassword.scan(O))
    mock.patch.stopall()
    router(onepassword, {'/auditevents': ({}, 403), '/signinattempts': {'items': []}, '/itemusages': {'items': []}})
    c = by_title(onepassword.scan(O))['1Password: MFA not disabled (audit events)']
    assert not c.passed and c.severity == 'Low' and '403' in c.detail
