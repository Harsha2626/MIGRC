import pytest
from botocore.exceptions import ClientError

from app.integrations import registry
from app.integrations.providers import aws

CFG = {'access_key_id': 'AKIATEST', 'secret_access_key': 'sekret', 'region': 'us-east-1'}


def err(code='AccessDenied'):
    return ClientError({'Error': {'Code': code, 'Message': 'x'}}, 'Op')


class Fake:
    """Returns canned values by method name; a value that is an Exception is raised; callable values are called."""
    def __init__(self, **m):
        self.m = m

    def __getattr__(self, name):
        def call(**kw):
            v = self.m[name]
            if isinstance(v, Exception):
                raise v
            return v(**kw) if callable(v) else v
        return call

    def get_paginator(self, op):
        outer = self
        class P:
            def paginate(self, **kw):
                v = outer.m[op]
                if isinstance(v, Exception):
                    raise v
                return [v(**kw) if callable(v) else v]
        return P()


def run(monkeypatch, check, **m):
    monkeypatch.setattr(aws, '_client', lambda cfg, svc: Fake(**m))
    return check(CFG)


def test_registry_and_spec():
    s = registry()['aws']
    assert s['name'] == 'Amazon Web Services' and s['category'] == 'Cloud Providers'
    assert [f['name'] for f in s['fields']] == ['access_key_id', 'secret_access_key', 'region']
    assert s['fields'][1]['secret']


def test_validate(monkeypatch):
    monkeypatch.setattr(aws, '_client', lambda c, s: Fake(get_caller_identity={'Account': '123456789012'}))
    assert aws.validate(CFG) == '123456789012'
    monkeypatch.setattr(aws, '_client', lambda c, s: Fake(get_caller_identity=err('InvalidClientTokenId')))
    with pytest.raises(ValueError):
        aws.validate(CFG)


def test_bad_region():
    assert not aws._s3_public({**CFG, 'region': 'evil.com/x'}).passed


FULL = {'PublicAccessBlockConfiguration': dict.fromkeys(
    ['BlockPublicAcls', 'IgnorePublicAcls', 'BlockPublicPolicy', 'RestrictPublicBuckets'], True)}
OPEN_ACL = {'Grants': [{'Grantee': {'URI': 'http://acs.amazonaws.com/groups/global/AllUsers'}}]}


def test_s3_public(monkeypatch):
    b = {'Buckets': [{'Name': 'a'}]}
    assert run(monkeypatch, aws._s3_public, list_buckets=b, get_public_access_block=FULL).passed
    c = run(monkeypatch, aws._s3_public, list_buckets=b, get_bucket_acl=OPEN_ACL, get_bucket_policy_status=err('NoSuchBucketPolicy'),
            get_public_access_block=err('NoSuchPublicAccessBlockConfiguration'))
    assert not c.passed and 'a' in c.detail
    c = run(monkeypatch, aws._s3_public, list_buckets=b, get_bucket_acl={'Grants': []},
            get_public_access_block=err('NoSuchPublicAccessBlockConfiguration'),
            get_bucket_policy_status={'PolicyStatus': {'IsPublic': True}})
    assert not c.passed
    assert run(monkeypatch, aws._s3_public, list_buckets=b, get_bucket_acl={'Grants': []},
               get_public_access_block=err('NoSuchPublicAccessBlockConfiguration'),
               get_bucket_policy_status=err('NoSuchBucketPolicy')).passed


def test_s3_enc(monkeypatch):
    b = {'Buckets': [{'Name': 'a'}]}
    assert run(monkeypatch, aws._s3_enc, list_buckets=b, get_bucket_encryption={}).passed
    assert not run(monkeypatch, aws._s3_enc, list_buckets=b,
                   get_bucket_encryption=err('ServerSideEncryptionConfigurationNotFoundError')).passed


def test_sg(monkeypatch):
    def sgs(perm):
        return {'SecurityGroups': [{'GroupId': 'sg-1', 'IpPermissions': [perm]}]}
    ok = {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
    assert run(monkeypatch, aws._sg_open, describe_security_groups=sgs(ok)).passed
    ssh = {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
    assert not run(monkeypatch, aws._sg_open, describe_security_groups=sgs(ssh)).passed
    allp = {'IpProtocol': '-1', 'Ipv6Ranges': [{'CidrIpv6': '::/0'}]}
    assert not run(monkeypatch, aws._sg_open, describe_security_groups=sgs(allp)).passed
    priv = {**ssh, 'IpRanges': [{'CidrIp': '10.0.0.0/8'}]}
    assert run(monkeypatch, aws._sg_open, describe_security_groups=sgs(priv)).passed


def test_root(monkeypatch):
    good = {'SummaryMap': {'AccountMFAEnabled': 1, 'AccountAccessKeysPresent': 0}}
    bad = {'SummaryMap': {'AccountMFAEnabled': 0, 'AccountAccessKeysPresent': 2}}
    assert run(monkeypatch, aws._root_mfa, get_account_summary=good).passed
    assert not run(monkeypatch, aws._root_mfa, get_account_summary=bad).passed
    assert run(monkeypatch, aws._root_keys, get_account_summary=good).passed
    assert not run(monkeypatch, aws._root_keys, get_account_summary=bad).passed


def test_user_mfa(monkeypatch):
    users = {'Users': [{'UserName': 'bob'}]}
    assert run(monkeypatch, aws._user_mfa, list_users=users, list_mfa_devices={'MFADevices': [{}]}).passed
    c = run(monkeypatch, aws._user_mfa, list_users=users, list_mfa_devices={'MFADevices': []})
    assert not c.passed and 'bob' in c.detail


def test_trail(monkeypatch):
    t = {'trailList': [{'Name': 't', 'TrailARN': 'arn', 'IsMultiRegionTrail': True}]}
    assert run(monkeypatch, aws._trail, describe_trails=t, get_trail_status={'IsLogging': True}).passed
    assert not run(monkeypatch, aws._trail, describe_trails=t, get_trail_status={'IsLogging': False}).passed
    assert not run(monkeypatch, aws._trail, describe_trails={'trailList': []}).passed


def test_ebs(monkeypatch):
    assert run(monkeypatch, aws._ebs, get_ebs_encryption_by_default={'EbsEncryptionByDefault': True}).passed
    assert not run(monkeypatch, aws._ebs, get_ebs_encryption_by_default={'EbsEncryptionByDefault': False}).passed


def test_rds(monkeypatch):
    db = lambda **k: {'DBInstances': [{'DBInstanceIdentifier': 'db1', **k}]}
    assert run(monkeypatch, aws._rds_public, describe_db_instances=db(PubliclyAccessible=False)).passed
    assert not run(monkeypatch, aws._rds_public, describe_db_instances=db(PubliclyAccessible=True)).passed
    assert run(monkeypatch, aws._rds_enc, describe_db_instances=db(StorageEncrypted=True)).passed
    assert not run(monkeypatch, aws._rds_enc, describe_db_instances=db(StorageEncrypted=False)).passed


def test_access_denied_every_check(monkeypatch):
    monkeypatch.setattr(aws, '_client', lambda c, s: Fake(**{k: err() for k in (
        'list_buckets', 'describe_security_groups', 'get_account_summary', 'list_users', 'describe_trails',
        'get_ebs_encryption_by_default', 'describe_db_instances')}))
    res = aws.scan(CFG)
    assert len(res) == 10 and all(r.title.startswith('AWS: ') for r in res)
    assert all(not r.passed and 'access denied' in r.detail and 'sekret' not in r.detail for r in res)
    assert len({r.title for r in res}) == 10
