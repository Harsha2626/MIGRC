"""Pluggable integration registry. Adding an integration = adding ONE module in
app/integrations/providers/ that defines SPEC (see below); connect/disconnect/scan routes, the
integrations-tab card, evidence, control mapping, AI review and risk creation are all generic.

SPEC = {
  'key': 'github',                      # unique, url-safe
  'name': 'GitHub', 'category': 'Version Control', 'icon': 'fab fa-github', 'color': 'blue',
  'capabilities': ['Branch protection', ...],
  'fields': [{'name': 'token', 'label': 'Personal access token', 'secret': True, 'placeholder': '...'}],
  'validate': fn(cfg) -> str,           # cheap authenticated call; returns an account label, raises on bad creds
  'scan': fn(cfg) -> [Check, ...],      # read-only API calls only
}
Providers MUST: send credentials only to a fixed vendor host (or one validated by regex - SSRF/token exfil),
use timeouts, and never put secrets in Check.detail.
"""
import importlib
import pkgutil
from collections import namedtuple

# severity feeds the Risk opened for a failed check: Critical/High/Medium/Low
Check = namedtuple('Check', 'title passed detail keywords severity', defaults=('High',))
CATEGORIES = ('Cloud Providers', 'Identity Providers', 'Version Control', 'Endpoint Management',
              'Vulnerability Scanners', 'HR Systems', 'Monitoring & Incident', 'SaaS Application')
_REGISTRY = {}


def registry():
    if not _REGISTRY:
        from app.integrations import providers
        for m in pkgutil.iter_modules(providers.__path__):
            spec = importlib.import_module(f'app.integrations.providers.{m.name}').SPEC
            _REGISTRY[spec['key']] = spec
    return _REGISTRY
