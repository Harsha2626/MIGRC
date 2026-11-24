from datetime import datetime, timedelta
from unittest import mock

import pytest
import requests

from app.integrations import registry
from app.integrations.providers import crowdstrike, intune

NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
OLD = (datetime.utcnow() - timedelta(days=60)).strftime('%Y-%m-%dT%H:%M:%SZ')


def resp(data, status=200):
    r = mock.Mock(status_code=status)
    r.json.return_value = data
    r.raise_for_status.side_effect = None if status < 400 else requests.HTTPError(response=r)
    return r


def by_title(cs, frag):
    return next(c for c in cs if frag in c.title)


def test_registry():
    for k in ('crowdstrike', 'intune'):
        assert registry()[k]['category'] == 'Endpoint Management'


CCFG = {'client_id': 'id', 'client_secret': 'SECRET'}
POL = {'prevention': {'applied': True}, 'sensor_update': {'applied': True}}


def cs_scan(hosts, status=200):
    def get(url, **kw):
        return resp({'resources': ['a', 'b']} if status < 400 else {}, status)
    with mock.patch('requests.post', side_effect=[resp({'access_token': 't'}), resp({'resources': hosts})]) as p, \
            mock.patch('requests.get', side_effect=get):
        out = crowdstrike.scan(CCFG)
    assert p.call_args_list[0][0][0] == 'https://api.crowdstrike.com/oauth2/token'
    return out


def test_crowdstrike_pass():
    h = [{'hostname': 'h1', 'serial_number': 'S1', 'last_seen': NOW, 'reduced_functionality_mode': 'no', 'device_policies': POL}]
    cs = cs_scan(h)
    assert len(cs) == 3 and all(c.passed for c in cs)


def test_crowdstrike_fail():
    h = [{'hostname': 'bad', 'serial_number': 'S2', 'last_seen': OLD, 'reduced_functionality_mode': 'yes',
          'device_policies': {'prevention': {'applied': False}, 'sensor_update': {'applied': True}}}]
    cs = cs_scan(h)
    assert not any(c.passed for c in cs) and 'bad (S2)' in by_title(cs, 'stale').detail
    assert 'SECRET' not in ''.join(c.detail for c in cs)


def test_crowdstrike_permission_failure():
    with mock.patch('requests.post', return_value=resp({'access_token': 't'})), mock.patch('requests.get', return_value=resp({}, 403)):
        cs = crowdstrike.scan(CCFG)
    assert len(cs) == 1 and not cs[0].passed


ICFG = {'tenant_id': '11111111-2222-3333-4444-555555555555', 'client_id': 'id', 'client_secret': 'SECRET'}


def intune_scan(rows, status=200):
    with mock.patch('requests.post', return_value=resp({'access_token': 't'})) as p, \
            mock.patch('requests.get', return_value=resp({'value': rows}, status)) as g:
        out = intune.scan(ICFG)
    assert p.call_args[0][0] == f"https://login.microsoftonline.com/{ICFG['tenant_id']}/oauth2/v2.0/token"
    assert g.call_args[1]['allow_redirects'] is False
    return out


def test_intune_pass_fail():
    good = {'deviceName': 'g', 'serialNumber': 'S1', 'isEncrypted': True, 'complianceState': 'compliant', 'lastSyncDateTime': NOW}
    assert all(c.passed for c in intune_scan([good]))
    bad = {'deviceName': 'bad', 'serialNumber': 'S2', 'isEncrypted': False, 'complianceState': 'noncompliant', 'lastSyncDateTime': OLD}
    cs = intune_scan([good, bad])
    assert not any(c.passed for c in cs) and 'bad (S2)' in by_title(cs, 'encryption').detail and 'g (S1)' not in by_title(cs, 'stale').detail


def test_intune_permission_failure():
    cs = intune_scan([], 403)
    assert len(cs) == 1 and not cs[0].passed


@pytest.mark.parametrize('t', ['evil.com/x', 'a b', '', 'x@evil.com', 'evil.com:443', 'a.com/../b'])
def test_intune_tenant_guard(t):
    with pytest.raises(ValueError):
        intune._headers({'tenant_id': t})
