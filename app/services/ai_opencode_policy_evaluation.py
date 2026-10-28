"""
AI-assisted policy evidence-sufficiency evaluation via a local OpenCode server.

Dispatches a policy's content plus its linked controls' evidence to the
`compliance-auditor` subagent running on this machine's local OpenCode
instance, and asks it to judge whether the evidence is sufficient and to
propose an updated policy draft addressing any gaps it finds.

This is local-machine-only by design: it talks to an OpenCode server already
running on localhost (OPENCODE_SERVER_URL / OPENCODE_SERVER_PASSWORD below).
There is no portable, hosted equivalent of this agent, so on any machine
without that server running, evaluate_policy() simply returns None - the same
fail-open philosophy as ai_evidence_review.py. It never touches the real
project directory: each call gets its own empty scratch directory, and the
session is created with a restrictive permission override (deny write/edit/
shell/browser) as defense in depth on top of that.
"""
import os
import re
import json
import base64
import shutil
import logging
import tempfile
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

DEFAULT_SERVER_URL = 'http://127.0.0.1:28894'
AGENT_ID = 'compliance-auditor'
REQUEST_TIMEOUT = 170  # seconds - covers session create + prompt + wait + message fetch;
# grows with how much evidence/content is in the prompt, so err generous

# Deny mutating/escape-hatch actions outright so an unattended run can't change
# anything; read stays allowed, which is harmless since the scratch directory
# we hand the session is always empty.
RESTRICTIVE_PERMISSIONS = [
    {'action': 'write', 'resource': '*', 'effect': 'deny'},
    {'action': 'edit', 'resource': '*', 'effect': 'deny'},
    {'action': 'shell', 'resource': '*', 'effect': 'deny'},
    {'action': 'bash', 'resource': '*', 'effect': 'deny'},
    {'action': 'browser', 'resource': '*', 'effect': 'deny'},
]

EVALUATION_CRITERIA = '''
## How to Evaluate

Judge this policy on BOTH of the following dimensions - a policy can fail on either one independently:

1. **Document structure and completeness.** A policy document must contain, with real substantive
   content (not placeholders or one-liners), all of:
   - Purpose - why the policy exists
   - Scope - who and what it applies to
   - Roles and Responsibilities - who owns, approves, and enforces it
   - Policy Requirements/Statements - the actual, specific, actionable rules (not vague intentions)
   - Enforcement / Compliance - what happens on violation
   - Review Cycle - how and when it gets reviewed
   A policy missing a section entirely, or with a section that is just a placeholder/empty
   statement of intent, is NOT structurally complete. Report each missing or inadequate section
   as its own entry in missing_items with control_code "DOCUMENT" and control_title naming the
   missing section (e.g. "Missing section: Enforcement").

2. **Evidence sufficiency per linked control.** For each linked control, judge whether the
   evidence listed actually demonstrates the control is implemented in practice (not just that
   the policy says it should be). Report each gap as its own missing_items entry using that
   control's real code and title.

Only mark the overall verdict "Sufficient" if the document is structurally complete AND every
linked control has adequate, approved evidence. "Partially Sufficient" means one dimension is
solid and the other has gaps. "Insufficient" means both dimensions have material gaps, or either
dimension has a severe one.
'''

RESULT_SCHEMA_INSTRUCTIONS = '''
Respond with ONLY a single fenced ```json code block (nothing before or after it) matching exactly this shape:
```json
{
  "verdict": "Sufficient" | "Partially Sufficient" | "Insufficient",
  "summary": "2-4 sentence overall assessment covering both document structure and evidence sufficiency",
  "missing_items": [
    {"control_code": "... or DOCUMENT", "control_title": "...", "issue": "...", "severity": "High" | "Medium" | "Low"}
  ],
  "updated_policy_content": "A revised version of the policy text that patches every gap you found - both missing/weak sections and anything the evidence gaps imply the policy should say. Empty string if the policy has no editable text content to revise."
}
```
Do not use any file, search, or shell tools - everything you need is already in this message. Do not explore the working directory.
'''


def _config():
    password = os.environ.get('OPENCODE_SERVER_PASSWORD')
    if not password:
        return None
    url = os.environ.get('OPENCODE_SERVER_URL', DEFAULT_SERVER_URL).rstrip('/')
    return url, password


def _request(base_url, password, method, path, body=None, timeout=REQUEST_TIMEOUT):
    auth = base64.b64encode(f'opencode:{password}'.encode()).decode()
    headers = {'Authorization': f'Basic {auth}'}
    data = None
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def _controls_context(policy):
    from app.models import EvidenceMapping, Evidence

    context = []
    for control in policy.controls:
        mappings = EvidenceMapping.query.filter_by(control_id=control.id).all()
        evidence = []
        for mapping in mappings:
            ev = Evidence.query.get(mapping.evidence_id)
            if ev and ev.organization_id == policy.organization_id:
                evidence.append({'title': ev.title, 'status': ev.status, 'description': ev.description})
        context.append({
            'code': control.code,
            'title': control.title,
            'evidence_requirement': control.evidence_requirement,
            'evidence': evidence,
        })
    return context


def _describe_content_state(policy):
    if policy.content_state == 'content':
        return policy.content or ''
    if policy.content_state == 'file':
        return (f'(This policy has no editable text - its content is an uploaded file '
                f'"{policy.file_name or "unnamed"}". Evaluate evidence sufficiency only; '
                f'leave updated_policy_content empty.)')
    if policy.content_state == 'external':
        return (f'(This policy has no editable text - it links to an external document '
                f'at {policy.external_url}. Evaluate evidence sufficiency only; '
                f'leave updated_policy_content empty.)')
    return '(No content has been recorded for this policy yet.)'


def _build_prompt(policy, controls_context):
    lines = [
        f'@{AGENT_ID} Evaluate whether the evidence below is sufficient to support this '
        'policy, acting as a skilled compliance auditor.',
        '',
        f'# Policy: {policy.name} (v{policy.version})',
        f'Framework: {policy.framework or "Not specified"}',
        f'Department: {policy.department or "Not specified"}',
        f'Status: {policy.status}',
        '',
        '## Policy Requirement',
        policy.requirement_text or 'No requirement text recorded.',
        '',
        '## Policy Content',
        _describe_content_state(policy),
        '',
        '## Linked Controls & Their Evidence',
    ]
    if not controls_context:
        lines.append('No controls are linked to this policy - evaluate based on the policy text and requirement alone.')
    for c in controls_context:
        lines.append(f'### {c["code"]} - {c["title"]}')
        lines.append(f'Evidence requirement: {c["evidence_requirement"] or "Not specified."}')
        if c['evidence']:
            for e in c['evidence']:
                lines.append(f'- "{e["title"]}" ({e["status"]}): {e["description"] or "No description."}')
        else:
            lines.append('- No evidence has been uploaded for this control.')
        lines.append('')
    lines.append(EVALUATION_CRITERIA)
    lines.append(RESULT_SCHEMA_INSTRUCTIONS)
    return '\n'.join(lines)


def _extract_json(text):
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if not match:
        match = re.search(r'(\{.*\})', text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except (ValueError, TypeError):
        return None


def evaluate_policy(policy):
    """
    Returns {"verdict", "summary", "missing_items", "updated_policy_content"} or None.

    None means no suggestion - the local OpenCode server isn't configured/reachable,
    the agent's reply couldn't be parsed, or the call timed out/failed. Callers
    should treat None as a no-op, not an error.
    """
    cfg = _config()
    if cfg is None:
        return None
    base_url, password = cfg

    controls_context = _controls_context(policy)
    scratch_dir = tempfile.mkdtemp(prefix='migrc_policy_eval_')
    session_id = None
    try:
        session = _request(base_url, password, 'POST', '/api/session', {
            'location': {'directory': scratch_dir},
            'title': f'Policy evaluation: {policy.name}',
            'permissions': RESTRICTIVE_PERMISSIONS,
        })
        session_id = session['data']['id']

        _request(base_url, password, 'POST', f'/api/session/{session_id}/prompt', {
            'text': _build_prompt(policy, controls_context),
            'agents': [{'name': AGENT_ID}],
        })

        _request(base_url, password, 'POST', f'/api/experimental/session/{session_id}/wait')

        messages = _request(base_url, password, 'GET', f'/api/session/{session_id}/message')
        assistant_messages = [m for m in (messages or {}).get('data', []) if m.get('type') == 'assistant']
        if not assistant_messages:
            logger.warning('OpenCode policy evaluation produced no assistant message for policy_id=%s', policy.id)
            return None
        last = max(assistant_messages, key=lambda m: m.get('time', {}).get('completed', 0))
        full_text = '\n'.join(p['text'] for p in last.get('content', []) if p.get('type') == 'text')

        result = _extract_json(full_text)
        if not result or 'verdict' not in result:
            logger.warning('OpenCode policy evaluation returned unparseable output for policy_id=%s', policy.id)
            return None
        result.setdefault('missing_items', [])
        result.setdefault('updated_policy_content', '')
        return result

    except (urllib.error.URLError, TimeoutError, OSError, KeyError, ValueError) as e:
        logger.exception('OpenCode policy evaluation failed for policy_id=%s: %s', policy.id, e)
        return None
    finally:
        if session_id:
            try:
                _request(base_url, password, 'DELETE', f'/api/session/{session_id}', timeout=15)
            except Exception:
                pass
        shutil.rmtree(scratch_dir, ignore_errors=True)
