"""Tests for the GitHub / GitLab / Bitbucket integration providers (requests mocked)."""
from datetime import datetime, timedelta, timezone

import pytest
import requests

from app.integrations import registry
from app.integrations.providers import bitbucket, github, gitlab

NOW = datetime.now(timezone.utc)
RECENT = (NOW - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
OLD = (NOW - timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%SZ')


class R:
    def __init__(self, status=200, body=None, links=None):
        self.status_code, self._b, self.links, self.text = status, body, links or {}, ''

    def json(self):
        return self._b

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


def route(monkeypatch, table, calls=None):
    """table: {url-suffix-or-prefix: R | callable(params)}; longest matching key wins."""
    def fake(url, params=None, **kw):
        assert kw.get('timeout') and kw.get('allow_redirects') is False
        assert url.startswith(('https://api.github.com', 'https://gitlab.com/', 'https://api.bitbucket.org'))
        if calls is not None:
            calls.append(url)
        key = max((k for k in table if url.endswith(k) or url.split('?')[0].endswith(k)), key=len, default=None)
        assert key, f'unmocked {url}'
        v = table[key]
        return v(params) if callable(v) else v
    monkeypatch.setattr(requests, 'get', fake)


def by_title(checks):
    return {c.title: c for c in checks}


def test_registry_discovers_vcs():
    reg = registry()
    for k, cat in (('github', 'Version Control'), ('gitlab', 'Version Control'), ('bitbucket', 'Version Control')):
        assert reg[k]['category'] == cat and callable(reg[k]['scan']) and callable(reg[k]['validate'])


# ---------------- GitHub ----------------
GH = {'token': 't', 'org': 'acme'}


def gh_table(protected=True, approved=True, secret='enabled', dep=204, repos=None, twofa=True):
    repos = repos if repos is not None else [
        {'name': 'a', 'default_branch': 'main', 'archived': False, 'private': True,
         'security_and_analysis': {'secret_scanning': {'status': secret}}},
        {'name': 'old', 'default_branch': 'main', 'archived': True, 'private': True}]
    return {
        '/orgs/acme/repos': R(200, repos),
        '/orgs/acme': R(200, {'login': 'acme', 'two_factor_requirement_enabled': twofa}),
        '/branches/main/protection': R(200, {'required_pull_request_reviews': {'required_approving_review_count': 1}})
        if protected else R(404, {'message': 'Branch not protected'}),
        '/repos/acme/a/pulls': R(200, [{'number': 1, 'merged_at': RECENT, 'updated_at': RECENT},
                                        {'number': 2, 'merged_at': None, 'updated_at': RECENT},
                                        {'number': 3, 'merged_at': OLD, 'updated_at': OLD}]),
        '/pulls/1/reviews': R(200, [{'state': 'APPROVED'}] if approved else [{'state': 'COMMENTED'}]),
        '/repos/acme/a/vulnerability-alerts': R(dep, None),
    }


def test_github_all_pass(monkeypatch):
    route(monkeypatch, gh_table())
    cs = github.scan(GH)
    assert len(cs) == 7 and all(c.title.startswith('GitHub: ') for c in cs)
    assert all(c.passed for c in cs if 'public' not in c.title), [c for c in cs if not c.passed]
    assert '1 merged PR(s) checked' in by_title(cs)['GitHub: merged pull requests (last 30 days) all had an approving review'].detail
    assert not any('archived' in c.detail or 'old' in c.detail.split() for c in cs)


def test_github_failures(monkeypatch):
    t = gh_table(protected=False, approved=False, secret='disabled', dep=404, twofa=False,
                 repos=[{'name': 'a', 'default_branch': 'main', 'archived': False, 'private': False}])
    route(monkeypatch, t)
    cs = github.scan(GH)
    assert not any(c.passed for c in cs)
    d = by_title(cs)
    assert 'a#1' in d['GitHub: merged pull requests (last 30 days) all had an approving review'].detail
    assert 'Public repositories: a' in d['GitHub: no unexpected public repositories'].detail


def test_github_pagination_and_host_pinning(monkeypatch):
    calls = []
    t = gh_table()
    page = {'n': 0}

    def repos(params):
        page['n'] += 1
        return R(200, [{'name': 'a', 'default_branch': 'main', 'archived': False, 'private': True,
                        'security_and_analysis': {'secret_scanning': {'status': 'enabled'}}}],
                 {'next': {'url': 'https://api.github.com/orgs/acme/repos?page=2'}} if page['n'] == 1 else {})
    t['/orgs/acme/repos'] = repos
    t['/orgs/acme/repos?page=2'] = repos
    route(monkeypatch, t, calls)
    github.scan(GH)
    assert page['n'] == 2
    # a Link header pointing at another host must never receive the token
    monkeypatch.setattr(requests, 'get', lambda url, **kw: (_ for _ in ()).throw(AssertionError(url)) if 'evil' in url
                        else R(200, [], {'next': {'url': 'https://evil.example/x'}}))
    assert github._pages('t', '/orgs/acme/repos') == []


def test_github_permission_denied(monkeypatch):
    t = gh_table()
    t['/branches/main/protection'] = R(403, {'message': 'Upgrade to GitHub Pro'})
    t['/repos/acme/a/vulnerability-alerts'] = R(403, {'message': 'forbidden'})
    route(monkeypatch, t)
    d = by_title(github.scan(GH))
    c = d['GitHub: default branch is protected on all active repositories']
    assert not c.passed and 'Could not evaluate' in c.detail and 'permission' in c.detail
    assert 'Could not evaluate' in d['GitHub: Dependabot alerts enabled on active repositories'].detail
    assert d['GitHub: organization requires two-factor authentication'].passed  # unaffected checks still run

    route(monkeypatch, {'/orgs/acme/repos': R(403, {'message': 'x'})})
    cs = github.scan(GH)
    assert len(cs) == 1 and not cs[0].passed and 'Could not list' in cs[0].detail


def test_github_validate_and_bad_org(monkeypatch):
    route(monkeypatch, {'/user': R(200, {}), '/orgs/acme': R(200, {'login': 'acme'})})
    assert github.validate(GH) == 'acme'
    with pytest.raises(ValueError):
        github.validate({'token': 't', 'org': '../x'})


# ---------------- GitLab ----------------
GL = {'token': 't', 'group': 'grp'}


def gl_table(protected=True, rules=1, approved=True, secret=True, twofa=True, vis='private'):
    return {
        '/groups/grp/projects': R(200, [{'id': 7, 'path_with_namespace': 'grp/a', 'default_branch': 'main', 'visibility': vis}]),
        '/groups/grp': R(200, {'full_path': 'grp', 'require_two_factor_authentication': twofa}),
        '/protected_branches/main': R(200, {}) if protected else R(404, {}),
        '/projects/7/approval_rules': R(200, [{'approvals_required': rules}]),
        '/projects/7/merge_requests': R(200, [{'iid': 5}]),
        '/merge_requests/5/approvals': R(200, {'approved_by': [{'user': {}}] if approved else []}),
        '/projects/7/security_settings': R(200, {'secret_push_protection_enabled': secret}),
    }


def test_gitlab_pass_fail_denied(monkeypatch):
    route(monkeypatch, gl_table())
    cs = gitlab.scan(GL)
    assert len(cs) == 6 and all(c.title.startswith('GitLab: ') for c in cs) and all(c.passed for c in cs)
    route(monkeypatch, gl_table(protected=False, rules=0, approved=False, secret=False, twofa=False, vis='public'))
    assert not any(c.passed for c in gitlab.scan(GL))
    t = gl_table()
    t['/projects/7/approval_rules'] = R(404, {})  # free tier: feature unavailable
    t['/merge_requests/5/approvals'] = R(403, {})
    route(monkeypatch, t)
    d = by_title(gitlab.scan(GL))
    assert 'Could not evaluate' in d['GitLab: approval rules require >= 1 approval'].detail
    assert 'Could not evaluate' in d['GitLab: merged merge requests (last 30 days) all had an approval'].detail
    assert d['GitLab: default branch is protected on all active projects'].detail.startswith('Could not evaluate')


def test_gitlab_pagination(monkeypatch):
    t = gl_table()
    n = {'c': 0}

    def projects(params):
        n['c'] += 1
        return R(200, [{'id': 7, 'path_with_namespace': 'grp/a', 'default_branch': 'main', 'visibility': 'private'}],
                 {'next': {'url': 'https://gitlab.com/api/v4/groups/grp/projects?page=2'}} if n['c'] == 1 else {})
    t['/groups/grp/projects'] = projects
    t['/groups/grp/projects?page=2'] = projects
    route(monkeypatch, t)
    gitlab.scan(GL)
    assert n['c'] == 2


def test_gitlab_validate(monkeypatch):
    route(monkeypatch, {'/groups/grp': R(200, {'full_path': 'grp'})})
    assert gitlab.validate(GL) == 'grp'
    with pytest.raises(ValueError):
        gitlab.validate({'token': 't', 'group': 'a b'})


# ---------------- Bitbucket ----------------
BB = {'username': 'u', 'app_password': 'p', 'workspace': 'ws'}


def bb_table(restrictions=True, approved=True, private=True):
    rules = [{'kind': 'push', 'pattern': 'main', 'branch_match_kind': 'glob'},
             {'kind': 'require_approvals_to_merge', 'value': 1, 'pattern': 'main', 'branch_match_kind': 'glob'}] if restrictions else []
    return {
        '/repositories/ws': R(200, {'values': [{'slug': 'a', 'is_private': private, 'mainbranch': {'name': 'main'}}]}),
        '/repositories/ws/a/branch-restrictions': R(200, {'values': rules}),
        '/repositories/ws/a/pullrequests': R(200, {'values': [{'id': 3}]}),
        '/pullrequests/3': R(200, {'participants': [{'approved': approved}]}),
    }


def test_bitbucket_pass_fail_denied(monkeypatch):
    route(monkeypatch, bb_table())
    cs = bitbucket.scan(BB)
    assert len(cs) == 4 and all(c.title.startswith('Bitbucket: ') and c.passed for c in cs)
    route(monkeypatch, bb_table(restrictions=False, approved=False, private=False))
    assert not any(c.passed for c in bitbucket.scan(BB))
    t = bb_table()
    t['/repositories/ws/a/branch-restrictions'] = R(403, {})
    route(monkeypatch, t)
    d = by_title(bitbucket.scan(BB))
    assert 'Could not evaluate' in d['Bitbucket: default branch requires >= 1 approval to merge'].detail
    assert d['Bitbucket: no unexpected public repositories'].passed


def test_bitbucket_pagination_and_validate(monkeypatch):
    t = bb_table()
    n = {'c': 0}

    def repos(params):
        n['c'] += 1
        return R(200, {'values': [{'slug': 'a', 'is_private': True, 'mainbranch': {'name': 'main'}}],
                       'next': 'https://api.bitbucket.org/2.0/repositories/ws?page=2' if n['c'] == 1 else None})
    t['/repositories/ws'] = repos
    t['/repositories/ws?page=2'] = repos
    route(monkeypatch, t)
    bitbucket.scan(BB)
    assert n['c'] == 2
    route(monkeypatch, {'/workspaces/ws': R(200, {'name': 'WS'})})
    assert bitbucket.validate(BB) == 'WS'
