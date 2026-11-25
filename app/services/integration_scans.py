"""Automated integration scans (Scrut-style): each connected provider is probed for security
misconfigurations; every check becomes one Evidence row (upserted by title) mapped to matching
controls, then the existing AI evidence review (ai_evidence_review) suggests a verdict per mapping.
A human still accepts/rejects - nothing here sets Evidence.status beyond 'Pending Review'.

A check is (title, passed, detail, keywords). Keywords pick controls by ILIKE over
title/description/evidence_requirement within the org's active frameworks.
"""
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse

import requests
from sqlalchemy import or_

import json

from app.integrations import Check, registry
from app.models import (db, Evidence, EvidenceMapping, Control, OrganizationFramework, AzureConnection,
                        OktaConnection, IntegrationConnection, Risk)
from app.services.crypto import decrypt
from app.services.ai_evidence_review import apply_review

log = logging.getLogger(__name__)
TIMEOUT = 20
MAX_CONTROLS_PER_CHECK = 4  # shortcut: keyword match is coarse; cap noise, tune keywords/upgrade to AI mapping later
STALE_DAYS = 90


def _get_all(url, headers, key='value'):
    out = []
    while url:
        r = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=False)
        r.raise_for_status()
        body = r.json()
        out += body.get(key, []) if isinstance(body, dict) else body
        url = body.get('nextLink') if isinstance(body, dict) else None
    return out


def scan_azure(conn):
    from app.routes.azure import _token, ARM
    h = {'Authorization': f'Bearer {_token(conn.tenant_id, conn.client_id, decrypt(conn.client_secret))}'}
    base = f'{ARM}/subscriptions/{conn.subscription_id}/providers'
    stor = _get_all(f'{base}/Microsoft.Storage/storageAccounts?api-version=2023-01-01', h)
    nsgs = _get_all(f'{base}/Microsoft.Network/networkSecurityGroups?api-version=2023-05-01', h)
    public = [s['name'] for s in stor if (s.get('properties') or {}).get('allowBlobPublicAccess')]
    nohttps = [s['name'] for s in stor if (s.get('properties') or {}).get('supportsHttpsTrafficOnly') is False]
    opn = []
    for n in nsgs:
        for r in (n.get('properties') or {}).get('securityRules', []):
            p = r.get('properties') or {}
            ports = [p.get('destinationPortRange')] + (p.get('destinationPortRanges') or [])
            src = p.get('sourceAddressPrefix')
            if (p.get('access') == 'Allow' and p.get('direction') == 'Inbound' and src in ('*', 'Internet', '0.0.0.0/0')
                    and any(x in ('*', '22', '3389') for x in ports)):
                opn.append(f"{n['name']}/{r.get('name')}")
    return [
        ('Azure: storage accounts block public blob access', not public,
         f'{len(stor)} storage account(s) scanned. Public blob access enabled on: {", ".join(public) or "none"}.',
         ['access control', 'data protection', 'cloud', 'public']),
        ('Azure: storage accounts enforce HTTPS (encryption in transit)', not nohttps,
         f'{len(stor)} storage account(s) scanned. HTTP allowed on: {", ".join(nohttps) or "none"}.',
         ['encryption', 'in transit', 'cryptograph']),
        ('Azure: no NSG rule exposes SSH/RDP to the internet', not opn,
         f'{len(nsgs)} network security group(s) scanned. Open inbound rules: {", ".join(opn) or "none"}.',
         ['network security', 'firewall', 'network']),
    ]


def scan_okta(conn):
    token = decrypt(conn.api_token)
    h = {'Authorization': f'SSWS {token}', 'Accept': 'application/json'}
    api = f'https://{conn.domain}/api/v1'

    def get(path, **kw):
        r = requests.get(f'{api}{path}', headers=h, timeout=TIMEOUT, allow_redirects=False, **kw)
        r.raise_for_status()
        return r
    mfa = [p for p in get('/policies', params={'type': 'MFA_ENROLL'}).json() if p.get('status') == 'ACTIVE']
    pw = [p for p in get('/policies', params={'type': 'PASSWORD'}).json() if p.get('status') == 'ACTIVE']
    min_len = max([((p.get('settings') or {}).get('password') or {}).get('complexity', {}).get('minLength', 0) or 0
                   for p in pw] or [0])
    users, url = [], f'{api}/users?limit=200&filter=status eq "ACTIVE"'
    while url:
        r = requests.get(url, headers=h, timeout=TIMEOUT, allow_redirects=False)
        r.raise_for_status()
        users += r.json()
        url = (r.links.get('next') or {}).get('url')
        if url and urlparse(url).hostname != conn.domain:
            break
    cutoff = (datetime.utcnow() - timedelta(days=STALE_DAYS)).strftime('%Y-%m-%dT%H:%M:%S')
    stale = [(u.get('profile') or {}).get('login', u['id']) for u in users if (u.get('lastLogin') or '') < cutoff]
    return [
        ('Okta: MFA enrollment policy is active', bool(mfa),
         f'{len(mfa)} active MFA enrollment policy(ies).', ['multi-factor', 'mfa', 'authentication']),
        ('Okta: password policy minimum length >= 12', min_len >= 12,
         f'Strongest active password policy minimum length: {min_len}.', ['password', 'authentication']),
        (f'Okta: no active accounts idle > {STALE_DAYS} days', not stale,
         f'{len(users)} active user(s). Idle/never-logged-in: {len(stale)}'
         + (f' ({", ".join(stale[:10])}{"..." if len(stale) > 10 else ""}).' if stale else '.'),
         ['access review', 'user access', 'deprovision', 'access rights']),
    ]


SCANNERS = {'azure': (AzureConnection, scan_azure), 'okta': (OktaConnection, scan_okta)}  # legacy per-provider tables
LEVELS = {'Critical': 5, 'High': 4, 'Medium': 3, 'Low': 2}  # mirrors risks.RISK_LEVEL_SCORES (avoids importing a route)
RISK_PREFIX = '[Scan] '


def known_providers():
    return list(SCANNERS) + list(registry())


def _load(org_id, provider):
    """(connection row, scan fn) or raises LookupError."""
    if provider in SCANNERS:
        model, fn = SCANNERS[provider]
        conn = model.query.filter_by(organization_id=org_id).first()
        if not conn:
            raise LookupError(f'{provider} not connected')
        return conn, (lambda: fn(conn))
    spec = registry().get(provider)
    conn = IntegrationConnection.query.filter_by(organization_id=org_id, provider=provider).first() if spec else None
    if not conn:
        raise LookupError(f'{provider} not connected')
    return conn, (lambda: spec['scan'](json.loads(decrypt(conn.config))))


def _controls_for(org_id, keywords):
    fw_ids = [f.framework_id for f in OrganizationFramework.query.filter_by(organization_id=org_id)]
    if not fw_ids or not keywords:
        return []
    conds = [c.ilike(f'%{k}%') for k in keywords for c in (Control.title, Control.evidence_requirement)]
    return Control.query.filter(Control.framework_id.in_(fw_ids), or_(*conds)).limit(MAX_CONTROLS_PER_CHECK).all()


def sync_risk(org_id, check, provider, control=None):
    """Failed check -> one Risk (created once, refreshed after). Passing check -> removes the Risk only if still
    untriaged ('Open'); one a human moved to treatment/accepted is left alone. Matched by title.
    Returns 'opened' | 'closed' | None."""
    title = (RISK_PREFIX + check.title)[:200]
    risk = Risk.query.filter_by(organization_id=org_id, title=title).first()
    if check.passed:
        if risk and risk.status == 'Open':
            db.session.delete(risk)
            return 'closed'
        return None
    desc = f'Detected by automated {provider} scan. {check.detail}'
    if risk:
        risk.description = desc
        return None
    sev = check.severity if check.severity in LEVELS else 'High'
    db.session.add(Risk(organization_id=org_id, title=title, description=desc, category='Technical', status='Open',
                        likelihood='Medium', impact=sev, score=LEVELS['Medium'] * LEVELS[sev],
                        linked_control_id=control.id if control else None,
                        created=datetime.utcnow().strftime('%Y-%m-%d')))
    return 'opened'


def run_scan(org, provider, ai=True):
    """Scan one provider. Returns (checks_total, checks_failed, mappings_created, risks_opened). Raises on API failure."""
    conn, do_scan = _load(org.id, provider)
    checks = [Check(*c) for c in do_scan()]
    now = datetime.utcnow()
    src, mapped, failed, opened = f'integration:{provider}', 0, 0, 0
    for check in checks:
        title, passed, detail, keywords = check[:4]
        failed += not passed
        ev = Evidence.query.filter_by(organization_id=org.id, source_type=src, title=title[:200]).first()
        if not ev:
            ev = Evidence(organization_id=org.id, source_type=src, title=title[:200])
            db.session.add(ev)
        ev.description = f'Automated scan {now:%Y-%m-%d %H:%M} UTC. Result: {"PASS" if passed else "FAIL"}. {detail}'
        ev.status, ev.audit_period_end = 'Pending Review', now.date()
        db.session.flush()
        have = {m.control_id for m in ev.evidence_mappings}
        controls = _controls_for(org.id, keywords)
        for ctrl in controls:
            if ctrl.id not in have:
                db.session.add(EvidenceMapping(evidence_id=ev.id, control_id=ctrl.id))
                mapped += 1
        db.session.flush()
        opened += sync_risk(org.id, check, provider, controls[0] if controls else None) == 'opened'
        if ai:
            m = ev.evidence_mappings.first()
            if m:
                apply_review(ev, m.control)
    conn.last_synced_at = now
    db.session.commit()
    return len(checks), failed, mapped, opened


def connected_providers(org_id):
    out = [p for p, (model, _) in SCANNERS.items() if model.query.filter_by(organization_id=org_id).first()]
    return out + [c.provider for c in IntegrationConnection.query.filter_by(organization_id=org_id) if c.provider in registry()]


def run_scans_for_org(org):
    """Scan every connected provider; one provider failing never blocks the rest. Returns {provider: result|error}."""
    res = {}
    for p in connected_providers(org.id):
        try:
            res[p] = run_scan(org, p)
        except Exception as exc:
            db.session.rollback()
            log.exception('integration scan failed: %s org=%s', p, org.id)
            res[p] = exc
    return res
