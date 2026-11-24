from unittest import mock

from app.integrations import registry
from app.integrations.providers import snyk, sonarcloud, tenable


class R:
    def __init__(self, data=None, code=200):
        self.data, self.status_code = data, code

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def by_title(checks):
    return {c.title: c for c in checks}


def test_registry():
    assert {'snyk', 'sonarcloud', 'tenable'} <= set(registry())
    for k in ('snyk', 'sonarcloud', 'tenable'):
        assert registry()[k]['category'] == 'Vulnerability Scanners'


def issue(i, sev, created='2020-01-01T00:00:00Z'):
    return {'id': i, 'attributes': {'title': f't{i}', 'effective_severity_level': sev, 'created_at': created}}


def test_snyk_fail_and_pagination():
    cfg = {'token': 'TOK', 'org_id': 'o1'}
    calls = []

    def get(url, **kw):
        calls.append(url)
        if len(calls) == 1:
            return R({'data': [issue(1, 'critical'), issue(2, 'high')], 'links': {'next': '/rest/orgs/o1/issues?starting_after=x'}})
        return R({'data': [issue(3, 'high', '2999-01-01T00:00:00Z')]})
    with mock.patch('requests.get', get):
        c = by_title(snyk.scan(cfg))
    assert len(calls) == 2 and calls[1].startswith('https://api.snyk.io/rest/')
    assert not c['Snyk: no open Critical issues'].passed
    h = c['Snyk: no open High issues older than 30 days']
    assert not h.passed and 'high=2' in h.detail and 'TOK' not in h.detail


def test_snyk_pass_and_foreign_next_link_ignored():
    with mock.patch('requests.get', return_value=R({'data': [issue(1, 'high', '2999-01-01T00:00:00Z')],
                                                    'links': {'next': 'https://evil.example/x'}})) as g:
        c = snyk.scan({'token': 't', 'org_id': 'o'})
    assert g.call_count == 1 and all(x.passed for x in c)


def test_snyk_403():
    with mock.patch('requests.get', return_value=R({}, 403)):
        c = snyk.scan({'token': 't', 'org_id': 'o'})
    assert len(c) == 2 and not any(x.passed for x in c) and 'refused' in c[0].detail


def sonar_get(vuln_total=0, gate='OK', hot=0, code=200):
    def get(url, params=None, **kw):
        if code != 200:
            return R({}, code)
        if url.endswith('search_projects'):
            return R({'components': [{'key': 'p1'}], 'paging': {'pageSize': 100, 'total': 1}})
        if url.endswith('project_status'):
            return R({'projectStatus': {'status': gate}})
        if url.endswith('issues/search'):
            return R({'total': vuln_total, 'issues': [{'message': 'SQLi'}] * min(vuln_total, 5)})
        return R({'paging': {'total': hot}})
    return get


def test_sonarcloud_pass_fail_403():
    cfg = {'token': 't', 'organization': 'o'}
    with mock.patch('requests.get', sonar_get()):
        assert all(c.passed for c in sonarcloud.scan(cfg))
    with mock.patch('requests.get', sonar_get(vuln_total=2, gate='ERROR', hot=3)):
        assert not any(c.passed for c in sonarcloud.scan(cfg))
    with mock.patch('requests.get', sonar_get(code=403)):
        c = sonarcloud.scan(cfg)
    assert len(c) == 3 and not any(x.passed for x in c)


def test_sonarcloud_validate():
    with mock.patch('requests.get', return_value=R({'organizations': [{'name': 'Acme'}]})):
        assert sonarcloud.validate({'token': 't', 'organization': 'o'}) == 'Acme'


def tenable_get(crit=(), high=(), assets=(), code=200):
    def get(url, params=None, headers=None, **kw):
        assert url.startswith('https://cloud.tenable.com') and 'X-ApiKeys' in headers
        if code != 200:
            return R({}, code)
        if url.endswith('/assets'):
            return R({'assets': list(assets)})
        v = crit if params['filter.0.value'] == 'Critical' else high
        return R({'vulnerabilities': list(v)})
    return get


def test_tenable_pass_fail_403():
    cfg = {'access_key': 'a', 'secret_key': 'SECRET'}
    fresh = {'id': '1', 'last_seen': '2999-01-01T00:00:00Z'}
    with mock.patch('requests.get', tenable_get(assets=[fresh])):
        assert all(c.passed for c in tenable.scan(cfg))
    v = {'plugin_id': 9, 'plugin_name': 'OpenSSL', 'severity': 4, 'count': 3}
    old = {'id': '2', 'fqdn': ['h.example'], 'last_seen': '2001-01-01T00:00:00Z'}
    with mock.patch('requests.get', tenable_get(crit=[v], high=[{**v, 'severity': 3}], assets=[old])):
        c = tenable.scan(cfg)
    assert not any(x.passed for x in c) and 'OpenSSL' in c[0].detail and 'h.example' in c[2].detail
    assert 'SECRET' not in ''.join(x.detail for x in c)
    with mock.patch('requests.get', tenable_get(code=403)):
        c = tenable.scan(cfg)
    assert len(c) == 3 and not any(x.passed for x in c)
