"""SonarCloud: quality gates, vulnerabilities, hotspots (sonarcloud.io only)."""
import requests

from app.integrations import Check

HOST, TIMEOUT, MAX_PROJECTS = 'https://sonarcloud.io', 30, 50
KW = ['secure development', 'vulnerability', 'vulnerabilities', 'technical vulnerabilit', 'code review',
      'source code', 'change management', 'penetration']


class Denied(Exception):
    pass


def _get(cfg, path, params=None):
    r = requests.get(HOST + path, params=params, timeout=TIMEOUT, allow_redirects=False,
                     headers={'Authorization': f'Bearer {cfg["token"]}'})
    if r.status_code in (401, 403):
        raise Denied(f'HTTP {r.status_code}')
    r.raise_for_status()
    return r.json()


def validate(cfg):
    orgs = _get(cfg, '/api/organizations/search', {'organizations': cfg['organization']}).get('organizations', [])
    if not orgs:
        raise ValueError('Organization not found or not visible to this token')
    return orgs[0].get('name') or cfg['organization']


def _projects(cfg):
    out, p = [], 1
    while len(out) < MAX_PROJECTS:
        d = _get(cfg, '/api/components/search_projects', {'organization': cfg['organization'], 'ps': 100, 'p': p})
        out += [c['key'] for c in d.get('components', [])]
        pg = d.get('paging') or {}
        if p * pg.get('pageSize', 100) >= pg.get('total', 0):
            break
        p += 1
    return out[:MAX_PROJECTS]


def _safe(title, perm, fn, severity):
    try:
        ok, detail = fn()
        return Check(title, ok, detail, KW, severity)
    except Denied as e:
        return Check(title, False, f'SonarCloud refused the call ({e}). Needs: {perm}.', KW, 'Medium')


def scan(cfg):
    try:
        projects = _projects(cfg)
    except Denied as e:
        d = f'SonarCloud refused the call ({e}). Needs a token with Browse access to the organization projects.'
        return [Check(t, False, d, KW, 'Medium') for t in (
            'SonarCloud: quality gate passing for all projects',
            'SonarCloud: no open Blocker/Critical vulnerabilities',
            'SonarCloud: security hotspots reviewed')]
    note = f'{len(projects)} project(s) checked (cap {MAX_PROJECTS}).'

    def gates():
        bad = [k for k in projects if (_get(cfg, '/api/qualitygates/project_status', {'projectKey': k})
                                       .get('projectStatus') or {}).get('status') == 'ERROR']
        return not bad, f'{note} Failing quality gate: {len(bad)} (e.g. {", ".join(bad[:5]) or "none"}).'

    def vulns():
        d = _get(cfg, '/api/issues/search', {'organization': cfg['organization'], 'types': 'VULNERABILITY',
                                             'severities': 'BLOCKER,CRITICAL', 'resolved': 'false', 'ps': 5})
        n = d.get('total', 0)
        names = ', '.join(i.get('message', i.get('key', ''))[:80] for i in d.get('issues', [])[:5]) or 'none'
        return n == 0, f'Open Blocker/Critical vulnerabilities: {n} (e.g. {names}).'

    def hotspots():
        bad = {}
        for k in projects:
            n = (_get(cfg, '/api/hotspots/search', {'projectKey': k, 'status': 'TO_REVIEW', 'ps': 1})
                 .get('paging') or {}).get('total', 0)
            if n:
                bad[k] = n
        tot = sum(bad.values())
        return not bad, f'{note} Hotspots awaiting review: {tot} in {len(bad)} project(s) (e.g. {", ".join(list(bad)[:5]) or "none"}).'
    return [
        _safe('SonarCloud: quality gate passing for all projects', 'Browse on projects', gates, 'High'),
        _safe('SonarCloud: no open Blocker/Critical vulnerabilities', 'Browse on projects', vulns, 'Critical'),
        _safe('SonarCloud: security hotspots reviewed', 'Browse on projects (security hotspots)', hotspots, 'Medium'),
    ]


SPEC = {
    'key': 'sonarcloud', 'name': 'SonarCloud', 'category': 'Vulnerability Scanners', 'icon': 'fas fa-code',
    'color': 'orange',
    'capabilities': ['Quality gate status', 'Blocker/Critical vulnerabilities', 'Security hotspot review'],
    'fields': [{'name': 'token', 'label': 'User token', 'secret': True, 'placeholder': 'SonarCloud token'},
               {'name': 'organization', 'label': 'Organization key', 'placeholder': 'my-org'}],
    'validate': validate, 'scan': scan,
}
