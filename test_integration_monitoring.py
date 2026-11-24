from unittest import mock

import pytest

from app.integrations import registry
from app.integrations.providers import datadog, pagerduty


class R:
    def __init__(self, data=None, code=200):
        self.data, self.status_code = data, code

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


DD = {'api_key': 'SECRETK', 'app_key': 'SECRETA', 'site': 'api.datadoghq.eu'}
PD = {'api_key': 'PDSECRET'}


def test_registry():
    for k in ('datadog', 'pagerduty'):
        assert registry()[k]['category'] == 'Monitoring & Incident'


def test_datadog_pass_fail_denied():
    ok = [{'overall_state': 'OK', 'message': 'x @slack-ops'}]
    with mock.patch('requests.get', return_value=R(ok)) as g:
        assert all(c.passed for c in datadog.scan(DD))
    assert g.call_args[0][0].startswith('https://api.datadoghq.eu/') and g.call_args[1]['allow_redirects'] is False
    bad = [{'overall_state': 'Alert', 'overall_state_modified': '2020-01-01T00:00:00Z', 'message': ''}]
    with mock.patch('requests.get', return_value=R(bad)):
        c = datadog.scan(DD)
    assert [x.passed for x in c] == [True, False, False] and 'SECRET' not in ''.join(x.detail for x in c)
    with mock.patch('requests.get', return_value=R([])):
        assert not datadog.scan(DD)[0].passed
    with mock.patch('requests.get', return_value=R({}, 403)):
        c = datadog.scan(DD)
    assert len(c) == 3 and not any(x.passed for x in c)


def test_datadog_site_allowlist():
    with mock.patch('requests.get') as g, pytest.raises(ValueError):
        datadog.validate({**DD, 'site': 'evil.example'})
    g.assert_not_called()


def test_pagerduty_pass_fail_denied():
    def get(url, params=None, **kw):
        assert url.startswith('https://api.pagerduty.com/') and kw['allow_redirects'] is False
        if url.endswith('escalation_policies'):
            return R({'escalation_policies': [{'id': 'P1'}]})
        if url.endswith('schedules'):
            return R({'schedules': [{'id': 'S1'}]})
        return R({'incidents': [{'created_at': '2999-01-01T00:00:00Z'}]})
    with mock.patch('requests.get', get):
        assert all(c.passed for c in pagerduty.scan(PD))

    def bad(url, params=None, **kw):
        if url.endswith('incidents'):
            return R({'incidents': [{'created_at': '2020-01-01T00:00:00Z'}]})
        return R({'escalation_policies': [], 'schedules': []})
    with mock.patch('requests.get', bad):
        c = pagerduty.scan(PD)
    assert not any(x.passed for x in c) and 'PDSECRET' not in ''.join(x.detail for x in c)
    with mock.patch('requests.get', return_value=R({}, 401)):
        c = pagerduty.scan(PD)
    assert len(c) == 3 and not any(x.passed for x in c)
