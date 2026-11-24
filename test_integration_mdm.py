from datetime import datetime, timedelta
from unittest import mock

import pytest
import requests

from app.integrations import registry
from app.integrations.providers import fleet, jamf, kandji

NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
OLD = (datetime.utcnow() - timedelta(days=60)).strftime('%Y-%m-%dT%H:%M:%SZ')


def resp(data, status=200):
    r = mock.Mock(status_code=status)
    r.json.return_value = data
    r.raise_for_status.side_effect = None if status < 400 else requests.HTTPError(response=r)
    return r


def by_title(checks, frag):
    return next(c for c in checks if frag in c.title)


def test_registry_discovers():
    reg = registry()
    for k in ('kandji', 'jamf', 'fleet'):
        assert reg[k]['category'] == 'Endpoint Management' and reg[k]['icon'] == 'fas fa-laptop'
        assert all('name' in f for f in reg[k]['fields'])


KCFG = {'subdomain': 'acme', 'region_host': 'api.kandji.io', 'api_token': 'SECRET'}


def kandji_get(fv_second=True, status=200):
    devs = [{'device_id': 'a', 'device_name': 'good', 'serial_number': 'S1', 'platform': 'Mac', 'os_version': '15.1', 'last_check_in': NOW},
            {'device_id': 'b', 'device_name': 'bad', 'serial_number': 'S2', 'platform': 'Mac', 'os_version': '13.0', 'last_check_in': OLD}]

    def get(url, **kw):
        if url.endswith('/devices'):
            return resp(devs)
        if status >= 400:
            return resp({}, status)
        good = url.endswith('/a/details')
        return resp({'filevault': {'filevault_enabled': 'Yes' if good or fv_second else 'No'},
                     'security_information': {'firewall_enabled': good}})
    return get


def test_kandji_pass_fail():
    with mock.patch('requests.get', side_effect=kandji_get(fv_second=True)):
        cs = kandji.scan(KCFG)
    assert by_title(cs, 'disk encryption').passed
    fw, osc = by_title(cs, 'firewall'), by_title(cs, 'OS current')
    assert not fw.passed and 'bad (S2)' in fw.detail
    assert not osc.passed and 'bad (S2)' in osc.detail and 'good (S1)' not in osc.detail
    assert 'SECRET' not in ''.join(c.detail for c in cs)
    with mock.patch('requests.get', side_effect=kandji_get(fv_second=False)):
        assert not by_title(kandji.scan(KCFG), 'disk encryption').passed


def test_kandji_permission_failure_is_a_check():
    with mock.patch('requests.get', side_effect=kandji_get(status=403)):
        cs = kandji.scan(KCFG)
    assert not by_title(cs, 'can read device details').passed
    assert not any('disk encryption' in c.title for c in cs)  # unknown signal -> no fake check


@pytest.mark.parametrize('cfg', [
    {'subdomain': 'acme', 'region_host': 'api.evil.com'}, {'subdomain': 'acme', 'region_host': 'x.api.kandji.io'},
    {'subdomain': 'a.evil.com/', 'region_host': 'api.kandji.io'}, {'subdomain': 'ac me', 'region_host': 'api.kandji.io'},
    {'subdomain': '', 'region_host': 'api.kandji.io'}])
def test_kandji_host_guard(cfg):
    with pytest.raises(ValueError):
        kandji.host(cfg)


def test_kandji_hosts_ok():
    assert kandji.host(KCFG) == 'acme.api.kandji.io'
    assert kandji.host({**KCFG, 'region_host': 'api.eu.kandji.io'}) == 'acme.api.eu.kandji.io'


@pytest.mark.parametrize('sub', ['a.evil.com', 'acme@evil.com', 'acme/x', 'acme:443', 'ACME_X'])
def test_jamf_host_guard(sub):
    with pytest.raises(ValueError):
        jamf.host({'subdomain': sub})


JCFG = {'subdomain': 'acme', 'client_id': 'id', 'client_secret': 'SECRET'}


def jamf_inv(enc='ENCRYPTED', fw=True):
    return {'totalCount': 1, 'results': [{'id': '1', 'general': {'name': 'mbp', 'lastContactTime': NOW},
            'hardware': {'serialNumber': 'J1'}, 'operatingSystem': {'version': '15.1'},
            'diskEncryption': {'bootPartitionEncryptionDetails': {'partitionFileVault2State': enc}},
            'security': {'firewallEnabled': fw}}]}


@pytest.mark.parametrize('enc,fw,ok', [('ENCRYPTED', True, True), ('DECRYPTED', False, False)])
def test_jamf_pass_fail(enc, fw, ok):
    with mock.patch('requests.post', return_value=resp({'access_token': 't'})) as p, \
            mock.patch('requests.get', return_value=resp(jamf_inv(enc, fw))):
        cs = jamf.scan(JCFG)
    assert p.call_args[0][0] == 'https://acme.jamfcloud.com/api/oauth/token'
    assert by_title(cs, 'disk encryption').passed is ok and by_title(cs, 'firewall').passed is ok
    assert by_title(cs, 'OS current').passed


def test_jamf_permission_failure():
    with mock.patch('requests.post', return_value=resp({'access_token': 't'})), \
            mock.patch('requests.get', return_value=resp({}, 403)):
        cs = jamf.scan(JCFG)
    assert len(cs) == 1 and not cs[0].passed


@pytest.mark.parametrize('url', [
    'http://fleet.example.com', 'https://127.0.0.1', 'https://localhost', 'https://10.0.0.5', 'https://2130706433',
    'https://0x7f.1', 'https://[::1]', 'https://fleet.local', 'https://user@fleet.example.com', 'https://fleet.example.com:8443',
    'https://fleet_x.example.com', 'https://169.254.169.254', 'ftp://fleet.example.com', '', 'https://metadata.internal'])
def test_fleet_ssrf_guard_rejects(url):
    with mock.patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]):
        with pytest.raises(ValueError):
            fleet.base_url({'url': url})


def test_fleet_rejects_private_resolution_and_accepts_public():
    with mock.patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('10.1.2.3', 443))]):
        with pytest.raises(ValueError):
            fleet.base_url({'url': 'https://fleet.example.com'})
    with mock.patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]):
        assert fleet.base_url({'url': 'https://Fleet.Example.com/'}) == 'https://fleet.example.com/api/v1/fleet'


def test_fleet_scan():
    hosts = {'hosts': [{'id': 1, 'hostname': 'h1', 'hardware_serial': 'F1', 'platform': 'darwin', 'os_version': 'macOS 15.1',
                        'seen_time': NOW, 'disk_encryption_enabled': True},
                       {'id': 2, 'hostname': 'h2', 'hardware_serial': 'F2', 'platform': 'ubuntu', 'os_version': 'Ubuntu 22.04',
                        'seen_time': OLD, 'disk_encryption_enabled': False}]}
    pols = {'policies': [{'name': 'Firewall on', 'passing_host_count': 2, 'failing_host_count': 0},
                         {'name': 'Screen lock 5min', 'passing_host_count': 1, 'failing_host_count': 1}]}

    def get(url, **kw):
        return resp(pols if 'policies' in url else hosts)
    with mock.patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]), \
            mock.patch('requests.get', side_effect=get):
        cs = fleet.scan({'url': 'https://fleet.example.com', 'api_token': 'SECRET'})
    enc, osc = by_title(cs, 'disk encryption'), by_title(cs, 'OS current')
    assert not enc.passed and 'h2 (F2)' in enc.detail
    assert not osc.passed and 'h2 (F2)' in osc.detail and 'h1' not in osc.detail
    assert by_title(cs, 'firewall').passed and not by_title(cs, 'screen lock').passed
    assert not any('antivirus' in c.title for c in cs)
