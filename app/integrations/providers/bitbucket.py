"""Bitbucket Cloud provider: change-management / code-review evidence. api.bitbucket.org only."""
import fnmatch
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests

from app.integrations import Check

API = 'https://api.bitbucket.org/2.0'
TIMEOUT = 20
MAX_REPOS = 100
MAX_PRS = 200     # shortcut: merged-PR sample capped (+ one page of 50 per repo)
WINDOW_DAYS = 30
P = 'Bitbucket: '
CHANGE = ['change management', 'code review', 'peer review', 'secure development', 'source code']


class _Denied(Exception):
    pass


def _get(cfg, url, params=None):
    r = requests.get(url, params=params, timeout=TIMEOUT, allow_redirects=False,
                     auth=(cfg['username'], cfg['app_password']))
    if r.status_code in (401, 403):
        raise _Denied(f'HTTP {r.status_code} - app password lacks the required scope (repositories/pullrequests read, admin for restrictions)')
    if r.status_code != 404:
        r.raise_for_status()
    return r


def _pages(cfg, path, params=None, cap=MAX_REPOS):
    out, url = [], API + path
    while url and len(out) < cap:
        body = _get(cfg, url, params).json()
        out += body.get('values', [])
        url, params = body.get('next'), None
        if url and (urlparse(url).hostname != 'api.bitbucket.org' or not url.startswith('https://')):
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


def _ws(cfg):
    ws = (cfg.get('workspace') or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', ws):
        raise ValueError('Invalid Bitbucket workspace slug')
    return ws


def validate(cfg):
    r = _get(cfg, f'{API}/workspaces/{_ws(cfg)}')
    if r.status_code == 404:
        raise ValueError('Bitbucket workspace not found or not visible to these credentials')
    return r.json().get('name') or r.json().get('slug') or cfg['workspace']


def _matches(rule, branch):
    if rule.get('branch_match_kind') == 'branching_model':
        return rule.get('branch_type') == 'production'  # shortcut: assumes production branch == default branch
    return fnmatch.fnmatchcase(branch, rule.get('pattern') or '')


def _protection(cfg, ws, repos):
    unprot, noreview = [], []
    for r in repos:
        branch = (r.get('mainbranch') or {}).get('name') or 'main'
        rules = [x for x in _pages(cfg, f"/repositories/{ws}/{r['slug']}/branch-restrictions", {'pagelen': 100}, 500)
                 if _matches(x, branch)]
        if not any(x.get('kind') in ('push', 'restrict_merges', 'force', 'delete') for x in rules):
            unprot.append(r['slug'])
        if not any(x.get('kind') == 'require_approvals_to_merge' and (x.get('value') or 0) >= 1 for x in rules):
            noreview.append(r['slug'])
    return unprot, noreview


def _merged(cfg, ws, repos):
    stamp = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)).strftime('%Y-%m-%dT%H:%M:%SZ')
    total, bad = 0, []
    for r in repos:
        base = f"{API}/repositories/{ws}/{r['slug']}/pullrequests"
        prs = _get(cfg, base, {'state': 'MERGED', 'q': f'updated_on>"{stamp}"',
                               'sort': '-updated_on', 'pagelen': 50}).json().get('values', [])
        for pr in prs:
            if total >= MAX_PRS:
                break
            total += 1
            full = _get(cfg, f"{base}/{pr['id']}").json()
            if not any(p.get('approved') for p in full.get('participants', [])):
                bad.append(f"{r['slug']}#{pr['id']}")
    return total, bad


def scan(cfg):
    ws = _ws(cfg)
    repos, err = _try(lambda: _pages(cfg, f'/repositories/{ws}', {'pagelen': 100}))
    if err:
        return [Check(P + 'repositories readable', False,
                      f'Could not list repositories: {err}.', CHANGE, 'High')]
    n = f'{len(repos)} repo(s) scanned. '
    prot = _try(lambda: _protection(cfg, ws, repos))
    prs = _try(lambda: _merged(cfg, ws, repos))
    pub = [r['slug'] for r in repos if not r.get('is_private')]
    return [
        _mk(P + 'default branch has branch restrictions on all repositories', CHANGE + ['branch protection', 'access control'],
            'High', prot, lambda d: (not d[0], f'{n}No push/merge restriction on default branch of: {_lst(d[0])}.')),
        _mk(P + 'default branch requires >= 1 approval to merge', CHANGE, 'High', prot,
            lambda d: (not d[1], f'{n}No "require approvals to merge" restriction on: {_lst(d[1])}.')),
        _mk(P + f'merged pull requests (last {WINDOW_DAYS} days) all had an approval', CHANGE, 'High', prs,
            lambda d: (not d[1], f'Code review results: {d[0]} merged PR(s) checked, {d[0] - len(d[1])} approved, '
                                 f'{len(d[1])} merged without approval. Offenders: {_lst(d[1])}.')),
        _mk(P + 'no unexpected public repositories', ['source code', 'data protection', 'access control', 'public'],
            'Low', (None, None), lambda _: (not pub, f'{n}Public repositories: {_lst(pub)}. Review that each is intentionally public.')),
    ]


SPEC = {
    'key': 'bitbucket', 'name': 'Bitbucket', 'category': 'Version Control', 'icon': 'fab fa-bitbucket', 'color': 'blue',
    'capabilities': ['Branch restrictions', 'Required approvals', 'Code review results (merged PRs)', 'Public repositories'],
    'fields': [
        {'name': 'username', 'label': 'Bitbucket username', 'secret': False, 'placeholder': 'username'},
        {'name': 'app_password', 'label': 'App password (repositories + pull requests read, admin)', 'secret': True, 'placeholder': ''},
        {'name': 'workspace', 'label': 'Workspace slug', 'secret': False, 'placeholder': 'my-workspace'},
    ],
    'validate': validate, 'scan': scan,
}
