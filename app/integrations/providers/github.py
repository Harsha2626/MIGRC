"""GitHub provider: change-management / code-review evidence. api.github.com only (token never leaves it)."""
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlparse

import requests

from app.integrations import Check

API = 'https://api.github.com'
TIMEOUT = 20
MAX_REPOS = 100
MAX_PRS = 200     # shortcut: merged-PR sample capped (+ one page of 50 per repo), raise if audits need full coverage
WINDOW_DAYS = 30
P = 'GitHub: '
CHANGE = ['change management', 'code review', 'peer review', 'secure development', 'source code']


class _Denied(Exception):
    pass


def _get(tok, url, params=None):
    r = requests.get(url, params=params, timeout=TIMEOUT, allow_redirects=False, headers={
        'Authorization': f'Bearer {tok}', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
    if r.status_code in (401, 403):
        try:
            msg = str(r.json().get('message', ''))[:120]
        except Exception:
            msg = ''
        raise _Denied(f'HTTP {r.status_code} - token lacks the required scope/permission ({msg})')
    if r.status_code != 404:
        r.raise_for_status()
    return r


def _pages(tok, path, params=None, cap=MAX_REPOS):
    out, url = [], API + path
    while url and len(out) < cap:
        r = _get(tok, url, params)
        out += r.json()
        url, params = (r.links.get('next') or {}).get('url'), None
        if url and (urlparse(url).hostname != 'api.github.com' or not url.startswith('https://')):
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


def validate(cfg):
    org = _org(cfg)
    _get(cfg['token'], f'{API}/user')
    r = _get(cfg['token'], f'{API}/orgs/{org}')
    if r.status_code == 404:
        raise ValueError('GitHub organization not found or not visible to this token')
    return r.json().get('login', org)


def _org(cfg):
    org = (cfg.get('org') or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9-]{1,39}', org):
        raise ValueError('Invalid GitHub organization login')
    return org


def _protection(tok, org, repos):
    unprot, noreview = [], []
    for r in repos:
        resp = _get(tok, f"{API}/repos/{org}/{r['name']}/branches/{quote(r.get('default_branch') or 'main', safe='')}/protection")
        if resp.status_code == 404:  # shortcut: repository rulesets are not consulted, so ruleset-only protection shows as unprotected
            unprot.append(r['name'])
            noreview.append(r['name'])
        elif ((resp.json().get('required_pull_request_reviews') or {}).get('required_approving_review_count') or 0) < 1:
            noreview.append(r['name'])
    return unprot, noreview


def _merged_prs(tok, org, repos):
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    stamp = cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')
    total, bad = 0, []
    for r in repos:
        resp = _get(tok, f"{API}/repos/{org}/{r['name']}/pulls", {
            'state': 'closed', 'sort': 'updated', 'direction': 'desc', 'per_page': 50})
        for pr in resp.json() if resp.status_code == 200 else []:
            if pr['updated_at'] < stamp:
                break
            if not pr.get('merged_at') or pr['merged_at'] < stamp or total >= MAX_PRS:
                continue
            total += 1
            rv = _get(tok, f"{API}/repos/{org}/{r['name']}/pulls/{pr['number']}/reviews", {'per_page': 100}).json()
            if not any(x.get('state') == 'APPROVED' for x in rv):
                bad.append(f"{r['name']}#{pr['number']}")
    return total, bad


def _dependabot(tok, org, repos):
    off = []
    for r in repos:
        if _get(tok, f"{API}/repos/{org}/{r['name']}/vulnerability-alerts").status_code != 204:
            off.append(r['name'])
    return off


def scan(cfg):
    tok, org = cfg['token'], _org(cfg)
    repos, err = _try(lambda: [r for r in _pages(tok, f'/orgs/{org}/repos', {'type': 'all', 'per_page': 100})
                               if not r.get('archived')][:MAX_REPOS])
    if err:
        return [Check(P + 'repositories readable', False,
                      f'Could not list repositories: {err}. Grant the token repo read + organization read access.',
                      CHANGE, 'High')]
    n = f'{len(repos)} active repo(s) scanned. '
    prot = _try(lambda: _protection(tok, org, repos))
    prs = _try(lambda: _merged_prs(tok, org, repos))
    deps = _try(lambda: _dependabot(tok, org, repos))
    org_r = _try(lambda: _get(tok, f'{API}/orgs/{org}').json())
    sec = [r['name'] for r in repos if ((r.get('security_and_analysis') or {}).get('secret_scanning') or {}).get('status') != 'enabled']
    pub = [r['name'] for r in repos if not r.get('private')]

    def twofa(o):
        v = o.get('two_factor_requirement_enabled')
        return (v is True, '2FA requirement is enabled for all members.' if v else
                '2FA requirement is disabled.' if v is False else
                '2FA setting not visible - token needs organization owner (admin:org read) access.')
    return [
        _mk(P + 'default branch is protected on all active repositories', CHANGE + ['branch protection', 'access control'],
            'High', prot, lambda d: (not d[0], f'{n}Default branch unprotected on: {_lst(d[0])}.')),
        _mk(P + 'default branch requires >= 1 approving pull request review', CHANGE, 'High', prot,
            lambda d: (not d[1], f'{n}Missing required PR approvals on: {_lst(d[1])}.')),
        _mk(P + f'merged pull requests (last {WINDOW_DAYS} days) all had an approving review', CHANGE, 'High', prs,
            lambda d: (not d[1], f'Code review results: {d[0]} merged PR(s) checked, {d[0] - len(d[1])} approved, '
                                 f'{len(d[1])} merged without approval. Offenders: {_lst(d[1])}.')),
        _mk(P + 'organization requires two-factor authentication', ['multi-factor', 'mfa', 'two-factor', 'authentication'],
            'High', org_r, twofa),
        _mk(P + 'secret scanning enabled on active repositories', ['secret', 'secure development', 'credential', 'vulnerab'],
            'Medium', (None, None), lambda _: (not sec, f'{n}Not confirmed enabled (disabled or not visible to the token) on: {_lst(sec)}.')),
        _mk(P + 'Dependabot alerts enabled on active repositories', ['vulnerab', 'patch', 'dependenc', 'secure development'],
            'Medium', deps, lambda d: (not d, f'{n}Dependabot alerts disabled on: {_lst(d)}.')),
        _mk(P + 'no unexpected public repositories', ['source code', 'data protection', 'access control', 'public'],
            'Low', (None, None), lambda _: (not pub, f'{n}Public repositories: {_lst(pub)}. Review that each is intentionally public.')),
    ]


SPEC = {
    'key': 'github', 'name': 'GitHub', 'category': 'Version Control', 'icon': 'fab fa-github', 'color': 'blue',
    'capabilities': ['Branch protection', 'Required PR reviews', 'Code review results (merged PRs)',
                     'Org 2FA', 'Secret scanning', 'Dependabot alerts', 'Public repositories'],
    'fields': [
        {'name': 'token', 'label': 'Personal access token (read-only)', 'secret': True, 'placeholder': 'ghp_... / github_pat_...'},
        {'name': 'org', 'label': 'Organization login', 'secret': False, 'placeholder': 'my-org'},
    ],
    'validate': validate, 'scan': scan,
}
