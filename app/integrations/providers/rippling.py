"""Rippling (API bearer token). Token is only sent to api.rippling.com. Output has counts/ids, never names."""
from datetime import date, timedelta

import requests

from app.integrations import Check
from app.integrations.providers.gusto import failed, hr_checks

TIMEOUT = 20


def _employees(cfg):
    r = requests.request('GET', 'https://api.rippling.com/platform/api/employees/include_terminated',
                         headers={'Authorization': f'Bearer {cfg.get("token", "")}', 'Accept': 'application/json'},
                         timeout=TIMEOUT, allow_redirects=False)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError('unexpected data')
    return data


def validate(cfg):
    _employees(cfg)
    return 'Rippling'


def scan(cfg):
    try:
        emps = _employees(cfg)
    except requests.HTTPError as e:
        code = e.response.status_code
        return failed('Rippling', f'Could not evaluate: API returned {code}'
                      + (' (token lacks access to employee data).' if code in (401, 403) else '.'))
    except (requests.RequestException, ValueError, KeyError):
        return failed('Rippling', 'Could not evaluate: request failed or returned unexpected data.')
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    act = [e for e in emps if e.get('roleState') == 'ACTIVE']
    term = [str(e.get('id')) for e in emps if (e.get('endDate') or '')[:10] >= cutoff and e.get('roleState') != 'ACTIVE']
    bad = [str(e.get('id')) for e in act if not e.get('startDate')]
    return hr_checks('Rippling', [str(e.get('id')) for e in act], term, bad, len(emps) - len(act))


SPEC = {
    'key': 'rippling', 'name': 'Rippling', 'category': 'HR Systems', 'icon': 'fas fa-address-card', 'color': 'yellow',
    'capabilities': ['Terminations (offboarding evidence)', 'HR data completeness', 'Headcount'],
    'fields': [{'name': 'token', 'label': 'API token', 'secret': True, 'placeholder': ''}],
    'validate': validate, 'scan': scan,
}
