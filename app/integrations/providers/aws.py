"""Amazon Web Services: read-only posture checks via boto3. Credentials go only to AWS endpoints (boto3 fixed hosts)."""
import re

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.integrations import Check

_CFG = Config(connect_timeout=5, read_timeout=15, retries={'max_attempts': 2})
_REGION = re.compile(r'^[a-z]{2}(-gov|-iso[a-z]?)?-[a-z]+-\d$')


def _client(cfg, svc):
    region = (cfg.get('region') or 'us-east-1').strip()
    if not _REGION.match(region):
        raise ValueError('Invalid AWS region')
    return boto3.client(svc, aws_access_key_id=cfg['access_key_id'], aws_secret_access_key=cfg['secret_access_key'],
                        region_name=region, config=_CFG)


def _pages(c, op, key, **kw):
    return [x for p in c.get_paginator(op).paginate(**kw) for x in p.get(key, [])]


def validate(cfg):
    try:
        return _client(cfg, 'sts').get_caller_identity()['Account']
    except (ClientError, BotoCoreError) as e:
        raise ValueError(f'AWS authentication failed: {getattr(e, "response", {}).get("Error", {}).get("Code", type(e).__name__)}')


def _guard(title, perm, keywords, severity):
    """Wrap a check fn(cfg)->(passed, detail); any API error becomes a failed Check naming the permission."""
    def deco(fn):
        def run(cfg):
            try:
                passed, detail = fn(cfg)
                return Check(title, passed, detail, keywords, severity)
            except ClientError as e:
                code = e.response.get('Error', {}).get('Code', 'Error')
                denied = code in ('AccessDenied', 'AccessDeniedException', 'UnauthorizedOperation', 'Forbidden', '403')
                msg = (f'Could not evaluate: access denied, grant {perm}.' if denied
                       else f'Could not evaluate ({code}); required permission: {perm}.')
            except (BotoCoreError, ValueError) as e:
                msg = f'Could not evaluate ({type(e).__name__}); required permission: {perm}.'
            return Check(title, False, msg, keywords, severity)
        return run
    return deco


def _list(names):
    return ', '.join(names[:10]) + ('...' if len(names) > 10 else '') if names else 'none'


@_guard('AWS: S3 buckets block public access', 's3:ListAllMyBuckets, s3:GetBucketPublicAccessBlock, s3:GetBucketAcl, s3:GetBucketPolicyStatus',
        ['access control', 'data protection', 'cloud', 'public'], 'Critical')
def _s3_public(cfg):
    s3 = _client(cfg, 's3')
    buckets = [b['Name'] for b in s3.list_buckets().get('Buckets', [])]
    public = []
    for b in buckets:
        try:
            pab = s3.get_public_access_block(Bucket=b)['PublicAccessBlockConfiguration']
            if all(pab.get(k) for k in ('BlockPublicAcls', 'IgnorePublicAcls', 'BlockPublicPolicy', 'RestrictPublicBuckets')):
                continue
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchPublicAccessBlockConfiguration':
                raise
        acl_public = any((g.get('Grantee') or {}).get('URI', '').endswith(('/AllUsers', '/AuthenticatedUsers'))
                         for g in s3.get_bucket_acl(Bucket=b)['Grants'])
        try:
            pol_public = s3.get_bucket_policy_status(Bucket=b)['PolicyStatus']['IsPublic']
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchBucketPolicy':
                raise
            pol_public = False
        if acl_public or pol_public:
            public.append(b)
    return not public, f'{len(buckets)} bucket(s) scanned. Publicly accessible: {_list(public)}.'


@_guard('AWS: S3 buckets have default encryption', 's3:ListAllMyBuckets, s3:GetEncryptionConfiguration',
        ['encryption', 'data protection', 'at rest', 'cryptograph'], 'High')
def _s3_enc(cfg):
    s3 = _client(cfg, 's3')
    buckets = [b['Name'] for b in s3.list_buckets().get('Buckets', [])]
    bad = []
    for b in buckets:
        try:
            s3.get_bucket_encryption(Bucket=b)
        except ClientError as e:
            if e.response['Error']['Code'] != 'ServerSideEncryptionConfigurationNotFoundError':
                raise
            bad.append(b)
    return not bad, f'{len(buckets)} bucket(s) scanned. Without default encryption: {_list(bad)}.'


@_guard('AWS: no security group exposes SSH/RDP to the internet', 'ec2:DescribeSecurityGroups',
        ['network security', 'firewall', 'network', 'remote access'], 'Critical')
def _sg_open(cfg):
    sgs = _pages(_client(cfg, 'ec2'), 'describe_security_groups', 'SecurityGroups')
    bad = []
    for sg in sgs:
        for p in sg.get('IpPermissions', []):
            world = any(r.get('CidrIp') == '0.0.0.0/0' for r in p.get('IpRanges', [])) or \
                any(r.get('CidrIpv6') == '::/0' for r in p.get('Ipv6Ranges', []))
            lo, hi = p.get('FromPort', 0), p.get('ToPort', 65535)
            if world and (p.get('IpProtocol') == '-1' or any(lo <= x <= hi for x in (22, 3389))):
                bad.append(sg['GroupId'])
                break
    return not bad, f'{len(sgs)} security group(s) scanned. Open to 0.0.0.0/0 on 22/3389: {_list(bad)}.'


def _summary(cfg):
    return _client(cfg, 'iam').get_account_summary()['SummaryMap']


@_guard('AWS: root account has MFA enabled', 'iam:GetAccountSummary',
        ['multi-factor', 'mfa', 'authentication', 'privileged'], 'Critical')
def _root_mfa(cfg):
    on = bool(_summary(cfg).get('AccountMFAEnabled'))
    return on, 'Root account MFA is enabled.' if on else 'Root account MFA is NOT enabled.'


@_guard('AWS: root account has no access keys', 'iam:GetAccountSummary',
        ['privileged', 'access control', 'credential', 'least privilege'], 'Critical')
def _root_keys(cfg):
    n = _summary(cfg).get('AccountAccessKeysPresent', 0)
    return n == 0, f'Root account access keys present: {n}.'


@_guard('AWS: all IAM users have MFA', 'iam:ListUsers, iam:ListMFADevices',
        ['multi-factor', 'mfa', 'authentication', 'user access'], 'High')
def _user_mfa(cfg):
    iam = _client(cfg, 'iam')
    users = [u['UserName'] for u in _pages(iam, 'list_users', 'Users')]
    bad = [u for u in users if not _pages(iam, 'list_mfa_devices', 'MFADevices', UserName=u)]
    return not bad, f'{len(users)} IAM user(s) scanned. Without MFA: {_list(bad)}.'


@_guard('AWS: multi-region CloudTrail is enabled and logging', 'cloudtrail:DescribeTrails, cloudtrail:GetTrailStatus',
        ['logging', 'monitoring', 'audit', 'log'], 'High')
def _trail(cfg):
    ct = _client(cfg, 'cloudtrail')
    good = [t['Name'] for t in ct.describe_trails().get('trailList', [])
            if t.get('IsMultiRegionTrail') and ct.get_trail_status(Name=t['TrailARN']).get('IsLogging')]
    return bool(good), f'Active multi-region trail(s): {_list(good)}.'


@_guard('AWS: EBS encryption by default is enabled', 'ec2:GetEbsEncryptionByDefault',
        ['encryption', 'data protection', 'at rest', 'cryptograph'], 'Medium')
def _ebs(cfg):
    on = bool(_client(cfg, 'ec2').get_ebs_encryption_by_default()['EbsEncryptionByDefault'])
    return on, f'EBS default encryption is {"enabled" if on else "disabled"} in region {cfg.get("region") or "us-east-1"}.'


def _rds(cfg):
    return _pages(_client(cfg, 'rds'), 'describe_db_instances', 'DBInstances')


@_guard('AWS: RDS instances are not publicly accessible', 'rds:DescribeDBInstances',
        ['network security', 'data protection', 'database', 'public'], 'Critical')
def _rds_public(cfg):
    dbs = _rds(cfg)
    bad = [d['DBInstanceIdentifier'] for d in dbs if d.get('PubliclyAccessible')]
    return not bad, f'{len(dbs)} RDS instance(s) scanned. Publicly accessible: {_list(bad)}.'


@_guard('AWS: RDS instances are encrypted at rest', 'rds:DescribeDBInstances',
        ['encryption', 'data protection', 'at rest', 'database'], 'High')
def _rds_enc(cfg):
    dbs = _rds(cfg)
    bad = [d['DBInstanceIdentifier'] for d in dbs if not d.get('StorageEncrypted')]
    return not bad, f'{len(dbs)} RDS instance(s) scanned. Unencrypted: {_list(bad)}.'


_CHECKS = [_s3_public, _s3_enc, _sg_open, _root_mfa, _root_keys, _user_mfa, _trail, _ebs, _rds_public, _rds_enc]


def scan(cfg):
    return [c(cfg) for c in _CHECKS]


SPEC = {
    'key': 'aws', 'name': 'Amazon Web Services', 'category': 'Cloud Providers', 'icon': 'fab fa-aws', 'color': 'orange',
    'capabilities': ['S3 public access and encryption', 'Security groups open to the internet', 'Root account MFA and keys',
                     'IAM users without MFA', 'CloudTrail', 'EBS and RDS encryption'],
    'fields': [
        {'name': 'access_key_id', 'label': 'Access key ID', 'placeholder': 'AKIA...'},
        {'name': 'secret_access_key', 'label': 'Secret access key (read-only user, e.g. SecurityAudit policy)', 'secret': True},
        {'name': 'region', 'label': 'Region', 'placeholder': 'us-east-1'},
    ],
    'validate': validate, 'scan': scan,
}
