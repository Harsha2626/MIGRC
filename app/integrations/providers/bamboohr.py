"""BambooHR (API key as basic-auth user). Key is only sent to api.bamboohr.com. Output has counts/ids, never names."""
import re
from datetime import date, timedelta

import requests

from app.integrations import Check

TIMEOUT = 20
SUB_RE = re.compile(r'^[a-z0-9-]+$')
FIELDS = ['id', 'status', 'hireDate', 'terminationDate', 'supervisorEId']


def _sub(cfg):
    s = (cfg.get('subdomain') or '').strip().lower()
    if not SUB_RE.match(s):
        raise ValueError('BambooHR subdomain may only contain a-z, 0-9 and hyphens')
    return s


def _employees(cfg):
    r = requests.request('POST', f'https://api.bamboohr.com/api/gateway.php/{_sub(cfg)}/v1/reports/custom',
                         params={'format': 'JSON', 'onlyCurrent': 'false'}, json={'fields': FIELDS},
                         auth=(cfg.get('api_key', ''), 'x'), headers={'Accept': 'application/json'},
                         timeout=TIMEOUT, allow_redirects=False)
    r.raise_for_status()
    return r.json().get('employees') or []


def validate(cfg):
    _employees(cfg)
    return _sub(cfg)


def _ids(items, n=10):
    return f' (ids: {", ".join(items[:n])}{"..." if len(items) > n else ""})' if items else ''


def _blank(v):
    return v in (None, '', '0000-00-00')


def scan(cfg):
    try:
        emps = _employees(cfg)
    except requests.HTTPError as e:
        code = e.response.status_code
        why = ' (API key user lacks access to employee reports).' if code in (401, 403) else '.'
        d = f'Could not evaluate: API returned {code}{why}'
    except (requests.RequestException, ValueError, KeyError):
        d = 'Could not evaluate: request failed or returned unexpected data.'
    else:
        d = None
    if d:
        return [Check(t, False, d, k, 'Low') for t, k in (
            ('BambooHR: recent terminations recorded', ['termination', 'offboarding', 'user access']),
            ('BambooHR: active employee records complete', ['onboarding', 'personnel', 'human resource']),
            ('BambooHR: headcount snapshot', ['human resource', 'personnel']))]
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    # BambooHR status values: 'Active' / 'Inactive'
    act = [e for e in emps if e.get('status') == 'Active']
    term = [str(e['id']) for e in emps if not _blank(e.get('terminationDate')) and e['terminationDate'] >= cutoff]
    bad = [str(e['id']) for e in act if _blank(e.get('hireDate')) or _blank(e.get('supervisorEId'))]
    return [
        Check('BambooHR: recent terminations recorded', True,
              f'{len(term)} employee(s) terminated in the last 30 days{_ids(term)}. Use as offboarding evidence '
              f'against IdP/account removal.', ['termination', 'offboarding', 'user access', 'deprovision'], 'Medium'),
        Check('BambooHR: active employee records complete', not bad,
              f'{len(act)} active employee(s); missing hire date or manager: {len(bad)}{_ids(bad)}.',
              ['onboarding', 'personnel', 'human resource', 'background'], 'Low'),
        Check('BambooHR: headcount snapshot', bool(act),
              f'{len(act)} active, {len(emps) - len(act)} inactive/terminated employee record(s).',
              ['human resource', 'personnel', 'onboarding'], 'Low'),
    ]


SPEC = {
    'key': 'bamboohr', 'name': 'BambooHR', 'category': 'HR Systems', 'icon': 'fas fa-users', 'color': 'green',
    'capabilities': ['Terminations (offboarding evidence)', 'HR data completeness', 'Headcount'],
    'fields': [
        {'name': 'subdomain', 'label': 'Company subdomain', 'placeholder': 'mycompany'},
        {'name': 'api_key', 'label': 'API key', 'secret': True, 'placeholder': ''}],
    'validate': validate, 'scan': scan,
}
