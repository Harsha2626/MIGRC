"""
Shared dispatch/retry/fallback plumbing for MIGRC's local-AI-assist features that talk to the
local OpenCode server (policy evidence-sufficiency evaluation, control evidence review).

Extracted from ai_opencode_policy_evaluation.py on 2026-10-30 when evidence review was rewired
onto the same pipeline, so the free-model fallback list, the cross-machine auditor lock, and the
Cline-direct bypass (see _cline_complete) live in exactly one place instead of two copies that
could drift out of sync - the Cline bypass in particular encodes a specific, non-obvious finding
(this OpenCode install gates custom/BYOK providers behind a subscription; Cline's own API works
fine called directly) that would be easy to silently lose if duplicated.

Callers build their own prompt text and their own JSON schema/parsing (policy evaluation and
evidence review ask for different shapes), then call run_compliance_agent(prompt, parse_fn).
This module only owns "get some model to answer this prompt" - trying each candidate model in
turn (OpenCode session API, or Cline's REST API directly for the 'clinedirect' pseudo-provider),
calling parse_fn on each reply, and moving on to the next candidate if parse_fn rejects it
(returns a falsy value) exactly as if that candidate had errored or timed out. Returns whatever
parse_fn returned, or None if every candidate was exhausted - callers treat None as "no
suggestion today", never as an exception to propagate (same fail-open philosophy throughout
MIGRC's AI-assist features).
"""
import os
import json
import time
import zlib
import base64
import shutil
import socket
import logging
import tempfile
import urllib.error
import urllib.request
from uuid import uuid4
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

DEFAULT_SERVER_URL = 'http://127.0.0.1:28894'
AGENT_ID = 'compliance-auditor'
REQUEST_TIMEOUT = 170  # seconds - covers session create + prompt + wait + message fetch;
# grows with how much evidence/content is in the prompt, so err generous
FALLBACK_REQUEST_TIMEOUT = 60  # shorter budget for 2nd/3rd model attempts - by then we're
# already in a degraded scenario and should fail fast rather than wait the full budget again

LOCK_WAIT_SECONDS = 45       # how long to queue for the auditor before giving up
LOCK_POLL_SECONDS = 2
LOCK_STALE_SECONDS = REQUEST_TIMEOUT + 60  # reclaim a lock left by a crashed/killed holder

REPLY_POLL_SECONDS = 2       # how often to check whether the agent has finished replying

# Model fallback: the PRIMARY path is the local OpenCode server's free `opencode` (Zen) provider
# models, which can intermittently return "Model is unavailable" under load or during
# provider-side incidents, or even an account-wide block (see
# https://github.com/anomalyco/opencode/issues/39827). Refreshed 2026-11-04 against the live
# server (`opencode models opencode --verbose` / GET /api/model). Ordered by context window with
# the stable models ahead of the "-alpha" previews. At call time the list is further reconciled
# with what the server reports (see _discover_free_models): deprecated/removed entries are
# dropped and newly-added active free models are appended, so this static list is only the
# fallback for when discovery fails. Set OPENCODE_MODEL="providerID/modelID" (and optionally
# OPENCODE_MODEL_VARIANT) to pin a single model instead. The Cline-direct bypass
# ("clinedirect/<model>") is OPT-IN ONLY via that same variable; it is never in the default list.
DEFAULT_FREE_MODELS = [
    ('opencode', 'nemotron-3.5-super-vl-free'),   # 1,048,576 ctx / 131,072 out
    ('opencode', 'beam-free'),                    # 1,048,576 ctx / 131,072 out
    ('opencode', 'crouton-alpha-free'),           # 1,048,576 ctx / 270,000 out (alpha)
    ('opencode', 'pulse-alpha-free'),             # 1,048,576 ctx / 131,072 out (alpha)
    ('opencode', 'flint-40b-free'),               # 262,144 ctx / 65,536 out
    ('opencode', 'nemotron-3.5-lightning-free'),  # 262,144 ctx / 262,144 out
    ('opencode', 'glm-5.3-flash-free'),           # 200,000 ctx / 32,000 out
    ('opencode', 'deepseek-v4.1-flash-free'),     # 200,000 ctx / 32,000 out
    ('opencode', 'mimo-v2.6-flash-free'),         # 200,000 ctx / 32,000 out
    ('opencode', 'big-pickle'),                   # 200,000 ctx / 32,000 out (free)
]

# Provider errors that mean "this account is gated", not "this model is down" (observed live
# 2026-11-04: HTTP 401 PAID_MODEL_AUTH_REQUIRED / HTTP 403 ENTITLEMENT_ERROR on every model).
AUTH_BLOCK_SIGNATURES = ('PAID_MODEL_AUTH_REQUIRED', 'ENTITLEMENT_ERROR')
AUTH_BLOCK_LIMIT = 3

# Vision-capable model used via Cline direct for image evidence (override: CLINE_VISION_MODEL).
DEFAULT_VISION_MODEL = 'xiaomi/mimo-v2.6-flash'

DISCOVERY_TTL_SECONDS = 300
DISCOVERY_TIMEOUT = 3
_discovery_cache = {'at': 0.0, 'key': None, 'models': None}

CLINE_API_URL = 'https://api.cline.bot/api/v1/chat/completions'
CLINE_SYSTEM_PROMPT = (
    'You are a skilled compliance auditor. Everything you need is already included in the '
    'message you receive. Do not explore any filesystem, run commands, fetch URLs, or write/edit '
    'files; just read what is given and respond. Follow the evaluation criteria and output '
    'format specified in the prompt exactly. Respond with ONLY the requested fenced JSON block - '
    'no extra prose before or after it.'
)

STATUS_CHECK_TIMEOUT = 2  # seconds - this is a UI status ping, not a real call; fail fast


def _cline_complete(prompt_text, model_id, timeout, images=None):
    """
    Calls Cline's hosted API (api.cline.bot) directly over plain HTTP, bypassing the local
    OpenCode server entirely, and returns the reply text.

    Why this exists rather than going through OpenCode like every other model here: this
    installed OpenCode version (1.19.5) appears to gate *custom* OpenAI-compatible providers
    (anything not in its own bundled models.dev catalog) behind an "OpenCode Go" subscription -
    confirmed 2026-10-30 by pointing a custom provider's baseURL at a deliberately unreachable
    address and still getting the identical `ENTITLEMENT_ERROR` response (i.e. OpenCode never
    even attempted the real network call). A direct, unauthenticated-by-OpenCode request to
    Cline's API with the same key and model succeeded repeatedly and reliably in the same testing.
    So for Cline specifically, callers talk to its REST API directly instead of routing through
    the local OpenCode server - this is the one model path that doesn't use `_request`/the
    OpenCode session API, the auditor lock, or the compliance-auditor agent config.
    """
    api_key = os.environ.get('CLINE_API_KEY')
    if not api_key:
        raise ValueError('CLINE_API_KEY is not set')
    user_content = prompt_text
    if images:  # images: [(mime, raw_bytes)] -> OpenAI-style multimodal content parts
        user_content = [{'type': 'text', 'text': prompt_text}] + [
            {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{base64.b64encode(raw).decode()}'}}
            for mime, raw in images
        ]
    body = json.dumps({
        'model': model_id,
        'temperature': 0.2,
        'top_p': 0.9,
        'messages': [
            {'role': 'system', 'content': CLINE_SYSTEM_PROMPT},
            {'role': 'user', 'content': user_content},
        ],
    }).encode('utf-8')
    req = urllib.request.Request(
        CLINE_API_URL, data=body, method='POST',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read())
    choice = (payload.get('data') or payload).get('choices', [{}])[0]
    return choice.get('message', {}).get('content', '')


def _discover_free_models(base_url, password):
    """Asks the live server which `opencode`-provider models are currently active and free
    (GET /api/model) and returns [(provider, model)] ordered by context window, or None if the
    server can't be asked. Cached for DISCOVERY_TTL_SECONDS. Never raises."""
    key = base_url
    now = time.monotonic()
    if _discovery_cache['key'] == key and now - _discovery_cache['at'] < DISCOVERY_TTL_SECONDS:
        return _discovery_cache['models']
    models = None
    try:
        payload = _request(base_url, password, 'GET', '/api/model', timeout=DISCOVERY_TIMEOUT)
        found = []
        for m in (payload or {}).get('data', []):
            if m.get('providerID') != 'opencode' or m.get('status') != 'active' or m.get('enabled') is False:
                continue
            costs = m.get('cost') or []
            if isinstance(costs, dict):
                costs = [costs]
            if not costs or any((c.get('input') or 0) or (c.get('output') or 0) for c in costs):
                continue  # not free
            found.append((m['id'], (m.get('limit') or {}).get('context') or 0))
        if found:
            found.sort(key=lambda x: -x[1])
            models = [('opencode', mid) for mid, _ in found]
    except Exception:
        models = None
    _discovery_cache.update(at=now, key=key, models=models)
    return models


def _default_models(base_url=None, password=None):
    """DEFAULT_FREE_MODELS reconciled with the live server: static order is preserved for
    entries the server still reports active, then any newly-added active free models are
    appended. Falls back to the static list verbatim if discovery is unavailable."""
    live = _discover_free_models(base_url, password) if base_url and password else None
    if not live:
        return list(DEFAULT_FREE_MODELS)
    live_set = set(live)
    ordered = [m for m in DEFAULT_FREE_MODELS if m in live_set]
    seen = set(ordered)
    ordered += [m for m in live if m not in seen]
    return ordered


def _candidate_models(base_url=None, password=None):
    """Returns a list of (provider_id, model_id, variant) tuples to try in order. `variant`
    is None unless OPENCODE_MODEL_VARIANT is set alongside a pinned OPENCODE_MODEL - e.g.
    "low" / "high" / "max" to select a reasoning-effort variant on models that expose one
    (confirmed via `opencode models <provider> --verbose`, which lists each model's
    `variants` map). DEFAULT_FREE_MODELS entries don't carry a variant since none of those
    free models advertise tunable reasoning-effort variants.

    A pinned OPENCODE_MODEL is used alone, unless OPENCODE_MODEL_FALLBACK=1, in which case the
    free OpenCode-server models follow it as fallbacks."""
    pinned = os.environ.get('OPENCODE_MODEL')
    if pinned and '/' in pinned:
        provider_id, model_id = pinned.split('/', 1)
        variant = os.environ.get('OPENCODE_MODEL_VARIANT') or None
        pinned_list = [(provider_id, model_id, variant)]
        if os.environ.get('OPENCODE_MODEL_FALLBACK') == '1':
            defaults = [(p, m, None) for p, m in _default_models(base_url, password)]
            return pinned_list + [d for d in defaults if d[:2] != (provider_id, model_id)]
        return pinned_list
    models = [(p, m, None) for p, m in _default_models(base_url, password)]
    # Safety net: if the OpenCode server is gated/unavailable, fall through to Cline-direct as the
    # LAST candidate (only when a key is configured). OpenCode stays the primary path.
    if os.environ.get('CLINE_API_KEY') and os.environ.get('CLINE_FALLBACK', '1') != '0':
        models.append(('clinedirect', os.environ.get('CLINE_FALLBACK_MODEL', 'minimax/minimax-m2.5'), None))
    return models


def _config():
    password = os.environ.get('OPENCODE_SERVER_PASSWORD')
    if not password:
        return None
    url = os.environ.get('OPENCODE_SERVER_URL', DEFAULT_SERVER_URL).rstrip('/')
    return url, password


def check_server_status():
    """
    Lightweight, synchronous reachability check for the local OpenCode server, for status
    indicators in the UI (e.g. the Setup Wizard) - does not create a session or touch the
    auditor lock, and says nothing about the Cline-direct path (which doesn't use this server).

    Returns one of:
      'not_configured' - OPENCODE_SERVER_PASSWORD isn't set on this machine.
      'connected'      - a server answered a minimal authenticated request within
                          STATUS_CHECK_TIMEOUT.
      'unreachable'    - OPENCODE_SERVER_PASSWORD is set but no server responded.
    """
    cfg = _config()
    if cfg is None:
        return 'not_configured'
    base_url, password = cfg
    try:
        _request(base_url, password, 'GET', '/api/session', timeout=STATUS_CHECK_TIMEOUT)
        return 'connected'
    except Exception:
        return 'unreachable'


def get_ai_status():
    """
    Secret-free description of which model path is active, for the Setup Wizard / a status
    endpoint. Never includes the password, API keys, or credentials.

    {'server': check_server_status() value ('cline-direct' reports whether CLINE_API_KEY exists),
     'path': 'opencode-server' | 'cline-direct',
     'primary_model': 'provider/model' or None,
     'fallback_count': int,
     'pinned': bool}
    """
    pinned = os.environ.get('OPENCODE_MODEL')
    pinned = pinned if pinned and '/' in pinned else None
    cline = bool(pinned) and pinned.split('/', 1)[0] == 'clinedirect'
    if cline:
        server = 'connected' if os.environ.get('CLINE_API_KEY') else 'not_configured'
    else:
        server = check_server_status()
    cfg = _config()
    candidates = _candidate_models(*cfg) if (cfg and server == 'connected') else _candidate_models()
    first = candidates[0] if candidates else None
    return {
        'server': server,
        'path': 'cline-direct' if cline else 'opencode-server',
        'primary_model': f'{first[0]}/{first[1]}' if first else None,
        'fallback_count': max(len(candidates) - 1, 0),
        'pinned': bool(pinned),
    }


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


def untrusted(label, text):
    """Wraps a piece of user-submitted content (policy/evidence text) in an explicit delimiter
    so the prompt itself marks where operator instructions end and submitted data begins -
    prompt-injection mitigation. Callers' prompts must also instruct the model to treat
    <untrusted-content> as data to judge, never as something to obey."""
    text = text if text else '(empty)'
    return f'<untrusted-content source="{label}">\n{text}\n</untrusted-content>'


def _machine_lock_id(machine_id):
    """Deterministic AiAuditorLock.id for this machine - a stable, non-negative 31-bit int
    derived from the hostname - so each machine serializes against its own row instead of
    every machine sharing a single global id=1 row. See AiAuditorLock's docstring in
    app/models.py for why this is scoped per machine."""
    return zlib.crc32(machine_id.encode('utf-8')) & 0x7fffffff


def _acquire_auditor_lock(owner):
    from app.models import db, AiAuditorLock

    machine_id = socket.gethostname()
    lock_id = _machine_lock_id(machine_id)
    stale_cutoff = datetime.utcnow() - timedelta(seconds=LOCK_STALE_SECONDS)
    AiAuditorLock.query.filter(AiAuditorLock.id == lock_id, AiAuditorLock.locked_at < stale_cutoff).delete()
    db.session.commit()
    try:
        db.session.add(AiAuditorLock(id=lock_id, machine_id=machine_id, locked_by=owner, locked_at=datetime.utcnow()))
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        return False


def _release_auditor_lock(owner):
    from app.models import db, AiAuditorLock

    lock_id = _machine_lock_id(socket.gethostname())
    AiAuditorLock.query.filter_by(id=lock_id, locked_by=owner).delete()
    db.session.commit()


def _wait_for_reply(base_url, password, session_id, deadline):
    """
    Polls the session's messages until the agent's reply has finished (successfully or with an
    error) or `deadline` (a time.monotonic() timestamp) passes. There's no server-side "wait for
    completion" call that reliably works across OpenCode server versions, so this polls GET
    .../message instead - a turn is done once its newest assistant message carries time.completed.
    """
    while True:
        messages = _request(base_url, password, 'GET', f'/api/session/{session_id}/message')
        assistant_messages = [m for m in (messages or {}).get('data', []) if m.get('type') == 'assistant']
        if assistant_messages:
            last = max(assistant_messages, key=lambda m: m.get('time', {}).get('created', 0))
            if last.get('time', {}).get('completed'):
                return last
        if time.monotonic() >= deadline:
            return None
        time.sleep(REPLY_POLL_SECONDS)


def run_compliance_agent(prompt_text, parse_fn, log_tag='request', images=None):
    """
    Runs prompt_text through each candidate model in turn (see _candidate_models), calling
    parse_fn(reply_text) on every reply received. The first candidate whose parse_fn result is
    truthy wins and is returned immediately. A reply that parse_fn rejects (returns None or any
    other falsy value - e.g. missing a required key) is treated exactly like a network error or
    timeout: log it and move on to the next candidate, never raise.

    Returns parse_fn's result, or None if every candidate was exhausted (server unreachable,
    cross-machine lock busy, every model errored/timed out/returned unparseable output).
    `log_tag` is just a short label for this call's log lines (e.g. a policy or control id).
    """
    cfg = _config()
    candidates = _candidate_models(*cfg) if cfg else _candidate_models()
    if images:
        # Image requests go to Cline direct on a vision model only: the pinned/default text
        # models can't see images, and the free OpenCode models are entitlement-gated or too
        # slow (verified live 2026-11-05). No CLINE_API_KEY -> no suggestion (fail open).
        if not os.environ.get('CLINE_API_KEY'):
            logger.warning('AI dispatch (%s): image review needs CLINE_API_KEY, skipping', log_tag)
            return None
        candidates = [('clinedirect', os.environ.get('CLINE_VISION_MODEL', DEFAULT_VISION_MODEL), None)]
    needs_opencode_server = any(provider_id != 'clinedirect' for provider_id, _, _ in candidates)

    base_url = password = None
    owner = None
    if needs_opencode_server:
        if cfg is None:
            return None
        base_url, password = cfg

        owner = f'{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}'
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        acquired = _acquire_auditor_lock(owner)
        while not acquired and time.monotonic() < deadline:
            time.sleep(LOCK_POLL_SECONDS)
            acquired = _acquire_auditor_lock(owner)
        if not acquired:
            logger.warning('AI dispatch (%s): auditor busy, gave up waiting', log_tag)
            return None

    try:
        last_failure = None
        auth_blocks = 0
        opencode_gated = False
        for attempt, (provider_id, model_id, variant) in enumerate(candidates):
            if opencode_gated and provider_id != 'clinedirect':
                continue
            attempt_timeout = REQUEST_TIMEOUT if attempt == 0 else FALLBACK_REQUEST_TIMEOUT
            tag = f'{provider_id}/{model_id}' + (f' ({variant})' if variant else '')
            scratch_dir = tempfile.mkdtemp(prefix='migrc_ai_eval_')
            session_id = None
            try:
                if provider_id == 'clinedirect':
                    full_text = _cline_complete(prompt_text, model_id, attempt_timeout, images)
                else:
                    session = _request(base_url, password, 'POST', '/api/session', {
                        'location': {'directory': scratch_dir},
                        'agent': AGENT_ID,
                    })
                    session_id = session['data']['id']

                    model_selector = {'providerID': provider_id, 'modelID': model_id}
                    if variant:
                        model_selector['variant'] = variant
                    _request(base_url, password, 'POST', f'/api/session/{session_id}/prompt', {
                        'prompt': {'text': prompt_text},
                        'model': model_selector,
                    })

                    last = _wait_for_reply(base_url, password, session_id, time.monotonic() + attempt_timeout)
                    if last is None:
                        last_failure = f'{tag}: timed out waiting for a reply'
                        logger.warning('AI dispatch (%s) timed out using model %s', log_tag, tag)
                        continue
                    if last.get('error'):
                        last_failure = f'{tag}: {last["error"]}'
                        logger.warning('AI dispatch (%s) agent errored using model %s: %s', log_tag, tag, last['error'])
                        if any(sig in str(last['error']) for sig in AUTH_BLOCK_SIGNATURES):
                            auth_blocks += 1
                            if auth_blocks >= AUTH_BLOCK_LIMIT:
                                # Account-wide gate (not a per-model outage): the remaining models
                                # will fail identically, so fail fast instead of burning minutes.
                                logger.warning('AI dispatch (%s): %d consecutive entitlement/sign-in '
                                               'errors - server is gating models account-wide, skipping '
                                               'remaining OpenCode models', log_tag, auth_blocks)
                                opencode_gated = True
                        else:
                            auth_blocks = 0
                        continue
                    full_text = '\n'.join(p['text'] for p in last.get('content', []) if p.get('type') == 'text')

                parsed = parse_fn(full_text)
                if not parsed:
                    last_failure = f'{tag}: unparseable output'
                    logger.warning('AI dispatch (%s) returned unparseable output using model %s', log_tag, tag)
                    continue
                return parsed

            except Exception as e:  # fail open: an HTTP/shape/parse_fn bug must never become a 500
                last_failure = f'{tag}: {e}'
                logger.exception('AI dispatch (%s) failed using model %s: %s', log_tag, tag, e)
                continue
            finally:
                if session_id:
                    try:
                        # NB: creation uses /api/session but the live server (verified 2026-11-04)
                        # only deletes via the legacy /session/{id}; DELETE /api/session/{id}
                        # returns the web UI's HTML shell and leaves the session behind.
                        _request(base_url, password, 'DELETE', f'/session/{session_id}', timeout=15)
                    except Exception:
                        pass
                shutil.rmtree(scratch_dir, ignore_errors=True)

        logger.warning('AI dispatch (%s): every candidate model failed (last failure: %s)', log_tag, last_failure)
        return None
    finally:
        if owner:
            _release_auditor_lock(owner)
