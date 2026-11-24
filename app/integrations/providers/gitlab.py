"""GitLab provider: change-management / code-review evidence. gitlab.com only (token never leaves it)."""
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlparse

import requests

from app.integrations import Check

# shortcut: gitlab.com only, no self-hosted host (would need regex-validated host against token exfil/SSRF); add when requested
API = 'https://gitlab.com/api/v4'
TIMEOUT = 20
MAX_REPOS = 100
MAX_MRS = 200     # shortcut: merged-MR sample capped (+ one page of 50 per project)
WINDOW_DAYS = 30
P = 'GitLab: '
CHANGE = ['change management', 'code review', 'peer review', 'secure development', 'source code']


class _Denied(Exception):
    pass


def _get(tok, url, params=None, na404=False):
    r = requests.get(url, params=params, timeout=TIMEOUT, allow_redirects=False, headers={'PRIVATE-TOKEN': tok})
    if r.status_code in (401, 403) or (na404 and r.status_code == 404):
        raise _Denied(f'HTTP {r.status_code} - token lacks scope/role, or feature needs a higher GitLab tier')
    if r.status_code != 404:
        r.raise_for_status()
    return r


def _pages(tok, path, params=None, cap=MAX_REPOS):
    out, url = [], API + path
    while url and len(out) < cap:
        r = _get(tok, url, params)
        out += r.json()
        url, params = (r.links.get('next') or {}).get('url'), None
        if url and (urlparse(url).hostname != 'gitlab.com' or not url.startswith('https://')):
            break
    return out[:cap]


def _lst(items, n=5):
    return ', '.join(items[:n]) + ('...' if len(items) > n else '') if items else 'none'


def _try(fn):
    try:
        return fn(), None
    except _Denied as e:
        return None, str(e)


def _mk(title, kw, sev, res, build):
    data, err = res
    if err:
        return Check(title, False, f'Could not evaluate: {err}.', kw, sev)
    ok, detail = build(data)
    return Check(title, ok, detail, kw, sev)


def _grp(cfg):
    g = (cfg.get('group') or '').strip().strip('/')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*', g):
        raise ValueError('Invalid GitLab group path')
    return quote(g, safe='')


def validate(cfg):
    r = _get(cfg['token'], f'{API}/groups/{_grp(cfg)}')
    if r.status_code == 404:
        raise ValueError('GitLab group not found or not visible to this token')
    return r.json().get('full_path', cfg['group'])


def _protection(tok, repos):
    unprot, noreview = [], []
    for p in repos:
        b = quote(p.get('default_branch') or 'main', safe='')
        if _get(tok, f"{API}/projects/{p['id']}/protected_branches/{b}").status_code == 404:
            unprot.append(p['path_with_namespace'])
        rules = _get(tok, f"{API}/projects/{p['id']}/approval_rules", na404=True).json()
        if not any((x.get('approvals_required') or 0) >= 1 for x in rules):
            noreview.append(p['path_with_namespace'])
    return unprot, noreview


def _merged(tok, repos):
    stamp = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)).strftime('%Y-%m-%dT%H:%M:%SZ')
    total, bad = 0, []
    for p in repos:
        mrs = _get(tok, f"{API}/projects/{p['id']}/merge_requests", {
            'state': 'merged', 'updated_after': stamp, 'per_page': 50}).json()
        for mr in mrs:
            if total >= MAX_MRS:
                break
            total += 1
            ap = _get(tok, f"{API}/projects/{p['id']}/merge_requests/{mr['iid']}/approvals", na404=True).json()
            if not ap.get('approved_by'):
                bad.append(f"{p['path_with_namespace']}!{mr['iid']}")
    return total, bad


def _secret_push(tok, repos):
    off = []
    for p in repos:
        r = _get(tok, f"{API}/projects/{p['id']}/security_settings", na404=True).json()
        if not r.get('secret_push_protection_enabled'):
            off.append(p['path_with_namespace'])
    return off


def scan(cfg):
    tok, g = cfg['token'], _grp(cfg)
    repos, err = _try(lambda: _pages(tok, f'/groups/{g}/projects', {
        'include_subgroups': 'true', 'archived': 'false', 'per_page': 100}))
    if err:
        return [Check(P + 'projects readable', False,
                      f'Could not list projects: {err}. Grant the token read_api scope with Reporter+ role on the group.',
                      CHANGE, 'High')]
    n = f'{len(repos)} active project(s) scanned. '
    prot = _try(lambda: _protection(tok, repos))
    mrs = _try(lambda: _merged(tok, repos))
    sec = _try(lambda: _secret_push(tok, repos))
    grp = _try(lambda: _get(tok, f'{API}/groups/{g}').json())
    pub = [p['path_with_namespace'] for p in repos if p.get('visibility') == 'public']

    def twofa(o):
        v = o.get('require_two_factor_authentication')
        return (v is True, '2FA requirement is enabled for all group members.' if v else '2FA requirement is disabled.')
    return [
        _mk(P + 'default branch is protected on all active projects', CHANGE + ['branch protection', 'access control'],
            'High', prot, lambda d: (not d[0], f'{n}Default branch unprotected on: {_lst(d[0])}.')),
        _mk(P + 'approval rules require >= 1 approval', CHANGE, 'High', prot,
            lambda d: (not d[1], f'{n}No approval rule requiring >= 1 approval on: {_lst(d[1])}.')),
        _mk(P + f'merged merge requests (last {WINDOW_DAYS} days) all had an approval', CHANGE, 'High', mrs,
            lambda d: (not d[1], f'Code review results: {d[0]} merged MR(s) checked, {d[0] - len(d[1])} approved, '
                                 f'{len(d[1])} merged without approval. Offenders: {_lst(d[1])}.')),
        _mk(P + 'group requires two-factor authentication', ['multi-factor', 'mfa', 'two-factor', 'authentication'],
            'High', grp, twofa),
        _mk(P + 'secret push protection enabled on active projects', ['secret', 'secure development', 'credential', 'vulnerab'],
            'Medium', sec, lambda d: (not d, f'{n}Secret push protection disabled on: {_lst(d)}.')),
        _mk(P + 'no unexpected public projects', ['source code', 'data protection', 'access control', 'public'],
            'Low', (None, None), lambda _: (not pub, f'{n}Public projects: {_lst(pub)}. Review that each is intentionally public.')),
    ]


SPEC = {
    'key': 'gitlab', 'name': 'GitLab', 'category': 'Version Control', 'icon': 'fab fa-gitlab', 'color': 'orange',
    'capabilities': ['Protected branches', 'Merge request approval rules', 'Code review results (merged MRs)',
                     'Group 2FA', 'Secret push protection', 'Public projects'],
    'fields': [
        {'name': 'token', 'label': 'Access token (read_api)', 'secret': True, 'placeholder': 'glpat-...'},
        {'name': 'group', 'label': 'Group path (gitlab.com)', 'secret': False, 'placeholder': 'my-group'},
    ],
    'validate': validate, 'scan': scan,
}
