"""Unit tests for the AI stream: dispatch fallback/model selection and questionnaire answering.
The HTTP layer (ai_dispatch._request / _cline_complete) is always mocked - no server needed."""
import json
import os
import tempfile

import pytest

from app.services import ai_dispatch, ai_questionnaire


@pytest.fixture
def app():
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    os.environ['DATABASE_URL'] = 'sqlite:///' + db_path
    os.environ['FLASK_ENV'] = 'development'
    from app import create_app
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    yield flask_app
    from app.models import db
    with flask_app.app_context():
        db.engine.dispose()
    os.environ.pop('DATABASE_URL', None)
    os.environ.pop('FLASK_ENV', None)
    os.remove(db_path)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ('OPENCODE_MODEL', 'OPENCODE_MODEL_VARIANT', 'OPENCODE_MODEL_FALLBACK',
              'OPENCODE_SERVER_URL', 'CLINE_API_KEY'):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv('OPENCODE_SERVER_PASSWORD', 'test-pass')
    ai_dispatch._discovery_cache.update(at=0.0, key=None, models=None)


# ---- model selection ----

def _model_payload(*specs):
    return {'data': [{'id': mid, 'providerID': 'opencode', 'status': status, 'enabled': True,
                      'cost': [{'input': cost, 'output': 0}], 'limit': {'context': ctx}}
                     for mid, status, cost, ctx in specs]}


def test_default_is_opencode_server_not_cline():
    cands = ai_dispatch._candidate_models()
    assert cands and all(p == 'opencode' for p, _, _ in cands)


def test_discovery_drops_deprecated_and_paid_and_appends_new(monkeypatch):
    payload = _model_payload(
        ('beam-free', 'active', 0, 1000),
        ('old-free', 'deprecated', 0, 9999),
        ('paid-model', 'active', 5, 9999),
        ('shiny-new-free', 'active', 0, 500),
    )
    monkeypatch.setattr(ai_dispatch, '_request', lambda *a, **k: payload)
    models = ai_dispatch._default_models('http://x', 'pw')
    assert models == [('opencode', 'beam-free'), ('opencode', 'shiny-new-free')]


def test_discovery_failure_falls_back_to_static(monkeypatch):
    def boom(*a, **k):
        raise OSError('down')
    monkeypatch.setattr(ai_dispatch, '_request', boom)
    assert ai_dispatch._default_models('http://x', 'pw') == ai_dispatch.DEFAULT_FREE_MODELS


def test_pinned_clinedirect_is_opt_in_and_alone(monkeypatch):
    monkeypatch.setenv('OPENCODE_MODEL', 'clinedirect/some/model')
    assert ai_dispatch._candidate_models() == [('clinedirect', 'some/model', None)]
    monkeypatch.setenv('OPENCODE_MODEL_FALLBACK', '1')
    cands = ai_dispatch._candidate_models()
    assert cands[0][0] == 'clinedirect' and len(cands) > 1


def test_get_ai_status_has_no_secrets(monkeypatch):
    monkeypatch.setattr(ai_dispatch, '_request', lambda *a, **k: _model_payload(('beam-free', 'active', 0, 1)))
    status = ai_dispatch.get_ai_status()
    assert status['path'] == 'opencode-server' and status['server'] == 'connected'
    assert status['primary_model'] == 'opencode/beam-free'
    assert 'test-pass' not in json.dumps(status)
    monkeypatch.setenv('OPENCODE_MODEL', 'clinedirect/x/y')
    monkeypatch.setenv('CLINE_API_KEY', 'sk-secret')
    status = ai_dispatch.get_ai_status()
    assert status['path'] == 'cline-direct' and 'sk-secret' not in json.dumps(status)


# ---- dispatch fallback ----

def _fake_server(monkeypatch, replies):
    """replies: model_id -> reply text (or None for an agent error). Records deletes."""
    state = {'session_model': {}, 'deleted': [], 'n': 0, 'current': None}

    def fake_request(base_url, password, method, path, body=None, timeout=None):
        if method == 'GET' and path == '/api/model':
            raise OSError('no discovery in this test')
        if method == 'POST' and path == '/api/session':
            state['n'] += 1
            return {'data': {'id': f's{state["n"]}'}}
        if method == 'POST' and path.endswith('/prompt'):
            state['session_model'][path.split('/')[3]] = body['model']['modelID']
            return None
        if method == 'GET' and path.endswith('/message'):
            model = state['session_model'][path.split('/')[3]]
            text = replies[model]
            msg = {'type': 'assistant', 'time': {'created': 1, 'completed': 2}}
            if text is None:
                msg['error'] = 'Model is unavailable'
            else:
                msg['content'] = [{'type': 'text', 'text': text}]
            return {'data': [msg]}
        if method == 'DELETE':
            state['deleted'].append(path)
            return True
        raise AssertionError(path)

    monkeypatch.setattr(ai_dispatch, '_request', fake_request)
    monkeypatch.setattr(ai_dispatch, '_acquire_auditor_lock', lambda owner: True)
    monkeypatch.setattr(ai_dispatch, '_release_auditor_lock', lambda owner: None)
    monkeypatch.setattr(ai_dispatch.time, 'sleep', lambda s: None)
    return state


def test_dispatch_falls_through_error_and_unparseable(monkeypatch):
    first, second, third = [m for _, m in ai_dispatch.DEFAULT_FREE_MODELS[:3]]
    replies = {m: 'garbage' for _, m in ai_dispatch.DEFAULT_FREE_MODELS}
    replies[first] = None            # agent error
    replies[second] = 'not json'     # parse_fn rejects
    replies[third] = 'OK:42'
    state = _fake_server(monkeypatch, replies)
    result = ai_dispatch.run_compliance_agent(
        'prompt', lambda t: t.split(':')[1] if t.startswith('OK:') else None)
    assert result == '42'
    assert [state['session_model'][f's{i}'] for i in (1, 2, 3)] == [first, second, third]
    # sessions are cleaned up via the legacy /session/{id} path that the live server honours
    assert state['deleted'] == ['/session/s1', '/session/s2', '/session/s3']


def test_dispatch_fails_fast_on_account_wide_entitlement_block(monkeypatch):
    blocked = "{'message': 'HTTP 403: ENTITLEMENT_ERROR'}"
    replies = {m: None for _, m in ai_dispatch.DEFAULT_FREE_MODELS}
    state = _fake_server(monkeypatch, replies)
    orig = ai_dispatch._request

    def with_err(base_url, password, method, path, body=None, timeout=None):
        res = orig(base_url, password, method, path, body, timeout)
        if method == 'GET' and path.endswith('/message'):
            res['data'][0]['error'] = blocked
        return res
    monkeypatch.setattr(ai_dispatch, '_request', with_err)
    assert ai_dispatch.run_compliance_agent('p', lambda t: t) is None
    assert len(state['session_model']) == ai_dispatch.AUTH_BLOCK_LIMIT  # not all 10 models


def test_dispatch_fail_open_when_parse_fn_raises(monkeypatch):
    replies = {m: 'x' for _, m in ai_dispatch.DEFAULT_FREE_MODELS}
    _fake_server(monkeypatch, replies)

    def bad(_):
        raise TypeError('boom')
    assert ai_dispatch.run_compliance_agent('p', bad) is None


def test_dispatch_returns_none_without_password(monkeypatch):
    monkeypatch.delenv('OPENCODE_SERVER_PASSWORD')
    assert ai_dispatch.run_compliance_agent('p', lambda t: t) is None


def test_dispatch_cline_direct_when_pinned(monkeypatch):
    monkeypatch.setenv('OPENCODE_MODEL', 'clinedirect/m/x')
    monkeypatch.setattr(ai_dispatch, '_cline_complete', lambda prompt, model, timeout, images=None: 'hello')
    assert ai_dispatch.run_compliance_agent('p', lambda t: t) == 'hello'


# ---- questionnaire parsing / sanity ----

POL = {3: 'Access Control Policy'}
EVI = {9: 'Q3 access review'}


def _reply(answers):
    return '```json\n' + json.dumps({'answers': answers}) + '\n```'


def test_parse_valid_answer_with_sources():
    out = ai_questionnaire.parse_suggestions(
        _reply([{'question_id': 'Q1', 'answer': 'Yes, we enforce MFA.', 'confidence': 0.9,
                 'cites': ['P3', 'e9']}]), {1, 2}, POL, EVI)
    s = out[1]
    assert s['cites'] == ['P3', 'E9'] and s['confidence'] == 0.9 and not s['needs_human']
    assert 'Access Control Policy' in s['accept_text'] and 'AI-suggested' in s['accept_text']


def test_parse_rejects_nonexistent_citation():
    out = ai_questionnaire.parse_suggestions(
        _reply([{'question_id': 'Q1', 'answer': 'We are SOC2.', 'confidence': 1, 'cites': ['P999']},
                {'question_id': 'Q2', 'answer': 'Yes', 'confidence': 0.5, 'cites': ['P3']}]),
        {1, 2}, POL, EVI)
    assert 1 not in out and 2 in out


def test_parse_all_rejected_returns_none_so_dispatch_tries_next_model():
    assert ai_questionnaire.parse_suggestions(
        _reply([{'question_id': 'Q1', 'answer': 'x', 'confidence': 1, 'cites': ['E5']}]), {1}, POL, EVI) is None


def test_parse_clamps_confidence_and_caps_uncited():
    out = ai_questionnaire.parse_suggestions(
        _reply([{'question_id': 'Q1', 'answer': 'a', 'confidence': 7, 'cites': ['P3']},
                {'question_id': 'Q2', 'answer': 'b', 'confidence': 0.99, 'cites': []},
                {'question_id': 'Q3', 'answer': 'c', 'confidence': 'high', 'cites': ['P3']}]),
        {1, 2, 3}, POL, EVI)
    assert out[1]['confidence'] == 1.0
    assert out[2]['confidence'] == ai_questionnaire.UNCITED_MAX_CONFIDENCE and out[2]['needs_human']
    assert out[3]['confidence'] == 0.0


def test_parse_drops_unknown_questions_dupes_and_junk():
    assert ai_questionnaire.parse_suggestions('no json here', {1}, POL, EVI) is None
    assert ai_questionnaire.parse_suggestions('{"answers": "nope"}', {1}, POL, EVI) is None
    out = ai_questionnaire.parse_suggestions(
        _reply([{'question_id': 'Q77', 'answer': 'a', 'cites': ['P3']},
                {'question_id': 'Q1', 'answer': '   ', 'cites': ['P3']},
                {'question_id': 'Q1', 'answer': 'first', 'confidence': .5, 'cites': ['P3']},
                {'question_id': 'Q1', 'answer': 'second', 'confidence': .5, 'cites': ['P3']},
                'junk']), {1}, POL, EVI)
    assert list(out) == [1] and out[1]['answer'] == 'first'


def test_parse_truncates_long_answers():
    out = ai_questionnaire.parse_suggestions(
        _reply([{'question_id': 'Q1', 'answer': 'z' * 10000, 'confidence': .5, 'cites': ['P3']}]),
        {1}, POL, EVI)
    assert len(out[1]['answer']) == ai_questionnaire.MAX_ANSWER_CHARS


# ---- org scoping ----

def test_context_and_prompt_are_org_scoped_and_untrusted(app, monkeypatch):
    from app.models import (db, Organization, Policy, Evidence, QuestionnaireTemplate,
                            QuestionnaireQuestion, Vendor, VendorAssessment)
    with app.app_context():
        a = Organization(name='A', slug='a')
        b = Organization(name='B', slug='b')
        db.session.add_all([a, b])
        db.session.flush()
        db.session.add_all([
            Policy(organization_id=a.id, name='A-Published', status='Published', content='alpha text'),
            Policy(organization_id=a.id, name='A-Draft', status='Draft', content='draft text'),
            Policy(organization_id=b.id, name='B-SECRET-POLICY', status='Published', content='b text'),
            Evidence(organization_id=a.id, title='A-Approved-Ev', status='Approved'),
            Evidence(organization_id=a.id, title='A-Pending-Ev', status='Pending Review'),
            Evidence(organization_id=b.id, title='B-SECRET-EVIDENCE', status='Approved'),
        ])
        tpl = QuestionnaireTemplate(organization_id=a.id, name='T')
        db.session.add(tpl)
        db.session.flush()
        q = QuestionnaireQuestion(template_id=tpl.id, question_text='Do you use MFA?')
        v = Vendor(organization_id=a.id, name='V')
        db.session.add_all([q, v])
        db.session.flush()
        asm = VendorAssessment(vendor_id=v.id, template_id=tpl.id)
        db.session.add(asm)
        db.session.commit()

        captured = {}

        def fake_run(prompt, parse_fn, log_tag=''):
            captured['prompt'] = prompt
            return parse_fn(_reply([{'question_id': f'Q{q.id}', 'answer': 'Yes', 'confidence': .8,
                                     'cites': ['P1']}]))
        monkeypatch.setattr(ai_questionnaire, 'run_compliance_agent', fake_run)

        result = ai_questionnaire.suggest_answers(asm, a.id)
        prompt = captured['prompt']
        assert 'A-Published' in prompt and 'A-Approved-Ev' in prompt
        for leaked in ('B-SECRET-POLICY', 'B-SECRET-EVIDENCE', 'A-Draft', 'A-Pending-Ev'):
            assert leaked not in prompt
        assert '<untrusted-content' in prompt
        assert result[q.id]['cites'] == ['P1']
        # nothing persisted by the service
        assert VendorAssessment.query.get(asm.id).responses.count() == 0


def test_suggest_answers_fails_open(app, monkeypatch):
    class T:  # assessment stub with no questions
        questions = []
    class A:
        id = 1
        template = T()
    with app.app_context():
        assert ai_questionnaire.suggest_answers(A(), 1) is None


def test_dispatch_images_use_cline_vision_model_only(monkeypatch):
    seen = {}
    def fake(prompt, model, timeout, images=None):
        seen.update(model=model, images=images)
        return 'ok'
    monkeypatch.setattr(ai_dispatch, '_cline_complete', fake)
    monkeypatch.setenv('CLINE_API_KEY', 'k')
    monkeypatch.delenv('OPENCODE_MODEL', raising=False)
    img = [('image/png', b'x')]
    assert ai_dispatch.run_compliance_agent('p', lambda t: t, images=img) == 'ok'
    assert seen == {'model': ai_dispatch.DEFAULT_VISION_MODEL, 'images': img}


def test_dispatch_images_without_cline_key_fails_open(monkeypatch):
    monkeypatch.delenv('CLINE_API_KEY', raising=False)
    assert ai_dispatch.run_compliance_agent('p', lambda t: t, images=[('image/png', b'x')]) is None


def test_load_content_kinds(tmp_path):
    from flask import Flask
    from app.services import ai_evidence_review as r
    app = Flask(__name__); app.config['UPLOAD_FOLDER'] = str(tmp_path)
    (tmp_path / 'a.csv').write_text('Activity,Lawful basis,Retention\n' + 'Payroll,Contract,7y\n' * 10)
    (tmp_path / 'b.png').write_bytes(b'x')
    (tmp_path / 'c.pptx').write_bytes(b'x')
    class E:
        def __init__(self, f): self.file_path = f
    with app.app_context():
        a, t, k = r._load_content(E('a.csv')); assert k == 'document' and 'Payroll' in t and a is None
        a, t, k = r._load_content(E('b.png')); assert k == 'image' and a[0][0] == 'image/png'
        assert r._load_content(E('c.pptx')) == (None, None, None)
        assert r._load_content(E('missing.pdf')) == (None, None, None)
