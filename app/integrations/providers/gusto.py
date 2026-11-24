"""Gusto (API bearer token). Token is only sent to api.gusto.com. Output has counts/ids, never names."""
import re
from datetime import date, timedelta

import requests

from app.integrations import Check

TIMEOUT = 20
UUID_RE = re.compile(r'^[A-Za-z0-9-]{8,64}$')
TITLES = (('recent terminations recorded', ['termination', 'offboarding', 'user access']),
          ('active employee records complete', ['onboarding', 'personnel', 'human resource']),
          ('headcount snapshot', ['human resource', 'personnel']))


def _company(cfg):
    c = (cfg.get('company_id') or '').strip()
    if not UUID_RE.match(c):
        raise ValueError('Gusto company ID may only contain letters, digits and hyphens')
    return c


def _employees(cfg, terminated):
    r = requests.request('GET', f'https://api.gusto.com/v1/companies/{_company(cfg)}/employees',
                         params={'terminated': str(terminated).lower(), 'per': 100},
                         headers={'Authorization': f'Bearer {cfg.get("token", "")}', 'Accept': 'application/json'},
                         timeout=TIMEOUT, allow_redirects=False)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError('unexpected data')
    return data


def validate(cfg):
    _employees(cfg, False)
    return _company(cfg)


def _ids(items, n=10):
    return f' (ids: {", ".join(items[:n])}{"..." if len(items) > n else ""})' if items else ''


def failed(name, d):
    return [Check(f'{name}: {t}', False, d, k, 'Low') for t, k in TITLES]


def hr_checks(name, act, term, bad, n_inactive):
    """act/term/bad: lists of employee ids (active, terminated in last 30d, active with incomplete record)."""
    return [
        Check(f'{name}: {TITLES[0][0]}', True,
              f'{len(term)} employee(s) terminated in the last 30 days{_ids(term)}. Use as offboarding evidence '
              f'against IdP/account removal.', TITLES[0][1] + ['deprovision'], 'Medium'),
        Check(f'{name}: {TITLES[1][0]}', not bad,
              f'{len(act)} active employee(s); incomplete onboarding or missing hire date: {len(bad)}{_ids(bad)}.',
              TITLES[1][1] + ['background'], 'Low'),
        Check(f'{name}: {TITLES[2][0]}', bool(act),
              f'{len(act)} active, {n_inactive} inactive/terminated employee record(s).', TITLES[2][1], 'Low'),
    ]


def scan(cfg):
    try:
        act, old = _employees(cfg, False), _employees(cfg, True)
    except requests.HTTPError as e:
        code = e.response.status_code
        return failed('Gusto', f'Could not evaluate: API returned {code}'
                      + (' (token lacks access to employee data).' if code in (401, 403) else '.'))
    except (requests.RequestException, ValueError, KeyError):
        return failed('Gusto', 'Could not evaluate: request failed or returned unexpected data.')
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    term = [str(e.get('uuid')) for e in old
            if any((t.get('effective_date') or '') >= cutoff for t in e.get('terminations') or [])]
    bad = [str(e.get('uuid')) for e in act
           if not e.get('onboarded', True) or not any(j.get('hire_date') for j in e.get('jobs') or [])]
    return hr_checks('Gusto', [str(e.get('uuid')) for e in act], term, bad, len(old))


SPEC = {
    'key': 'gusto', 'name': 'Gusto', 'category': 'HR Systems', 'icon': 'fas fa-user-tie', 'color': 'orange',
    'capabilities': ['Terminations (offboarding evidence)', 'Onboarding completeness', 'Headcount'],
    'fields': [
        {'name': 'company_id', 'label': 'Company ID (UUID)', 'placeholder': ''},
        {'name': 'token', 'label': 'API access token', 'secret': True, 'placeholder': ''}],
    'validate': validate, 'scan': scan,
}
