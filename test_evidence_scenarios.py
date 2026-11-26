"""Evidence upload / preview / review / delete scenarios (sqlite throwaway DB, AI mocked)."""
import importlib.util
import io
import json
import os

import pytest

from test_tenant_isolation import app, client, _org, _shared_fw, _adopt, _login  # noqa: F401

_spec = importlib.util.spec_from_file_location('gen', os.path.join(os.path.dirname(__file__), 'scripts', 'gen_iso_evidence.py'))
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


@pytest.fixture
def env(app, client, tmp_path, monkeypatch):
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'up')
    os.makedirs(app.config['UPLOAD_FOLDER'])
    monkeypatch.setattr('app.routes.compliance.apply_review', lambda ev, ctrl: False)  # no AI backend in tests
    org, uid = _org(app, 'Maritime', '@m.test')
    fw, cids = _shared_fw(app, n=3)
    _adopt(app, org, fw)
    _login(client, uid, org)
    files = tmp_path / 'f'
    gen.build(str(files))
    return dict(app=app, c=client, org=org, uid=uid, fw=fw, cids=cids, files=files)


def _up(e, fname, title='T', cid=0, extra=None, content=None):
    data = dict(title=title, description='d', source_type='Manual Upload')
    data.update(extra or {})
    body = content if content is not None else open(e['files'] / fname, 'rb').read()
    data['file'] = (io.BytesIO(body), fname)
    return e['c'].post(f"/compliance/{e['fw']}/control/{e['cids'][cid]}/upload", data=data, content_type='multipart/form-data')


def _ev(e):
    from app.models import Evidence
    with e['app'].app_context():
        return [(x.id, x.title, x.status, x.file_type, x.file_path, [m.control_id for m in x.evidence_mappings]) for x in Evidence.query.all()]


@pytest.mark.parametrize('fname,ext', [('ctx_4_1.pdf', 'pdf'), ('mdm_a81.png', 'png'), ('competence_72.csv', 'csv'),
                                       ('risk_register_612.xlsx', 'xlsx'), ('scope_4_3.docx', 'docx')])
def test_upload_each_type_and_preview(env, fname, ext):
    assert _up(env, fname).status_code == 302
    [(eid, title, status, ftype, path, maps)] = _ev(env)
    assert (ftype, status, maps) == (ext, 'Pending Review', [env['cids'][0]])
    assert os.path.isfile(os.path.join(env['app'].config['UPLOAD_FOLDER'], path))
    r = env['c'].get(f'/evidence/{eid}/preview')
    assert r.status_code == 200
    assert r.headers['X-Frame-Options'] == 'SAMEORIGIN' and r.headers['X-Content-Type-Options'] == 'nosniff'
    if ext in ('pdf', 'png'):
        assert r.mimetype == {'pdf': 'application/pdf', 'png': 'image/png'}[ext]
    else:
        assert r.mimetype == 'text/html' and b'<table>' in r.data
    page = env['c'].get(f"/compliance/{env['fw']}/control/{env['cids'][0]}").get_data(as_text=True)
    assert f'/evidence/{eid}/preview' in page


def test_upload_rejections(env):
    assert _ev(env) == []
    _up(env, 'x.exe', content=b'MZ')                      # disallowed type
    _up(env, 'a.pdf', title='', content=b'%PDF')          # missing title
    r = env['c'].post(f"/compliance/{env['fw']}/control/{env['cids'][0]}/upload", data=dict(title='t'))  # no file
    assert r.status_code == 302 and _ev(env) == []


def test_multi_control_mapping_and_foreign_control_ignored(env):
    other_fw, other_c = _shared_fw(env['app'], name='NotAdopted', n=1)
    _up(env, 'ctx_4_1.pdf', extra={'map_controls': [str(env['cids'][1]), str(other_c[0])]})
    [(*_, maps)] = _ev(env)
    assert sorted(maps) == sorted([env['cids'][0], env['cids'][1]])


def test_preview_escapes_html_in_csv(env):
    _up(env, 'x.csv', content=b'a,b\n<script>alert(1)</script>,2\n')
    r = env['c'].get(f"/evidence/{_ev(env)[0][0]}/preview")
    assert b'<script>' not in r.data and b'&lt;script&gt;' in r.data


def test_preview_tenant_isolation_and_auth(env, app):
    _up(env, 'ctx_4_1.pdf')
    eid = _ev(env)[0][0]
    other, uo = _org(app, 'Other', '@o.test')
    c2 = app.test_client()
    assert c2.get(f'/evidence/{eid}/preview').status_code in (301, 302, 401)   # anonymous
    _login(c2, uo, other)
    assert c2.get(f'/evidence/{eid}/preview').status_code == 404               # other tenant


def test_preview_missing_file_and_unknown_id(env):
    _up(env, 'ctx_4_1.pdf')
    eid, *_, path, _m = _ev(env)[0][0], *_ev(env)[0][1:]
    os.remove(os.path.join(env['app'].config['UPLOAD_FOLDER'], _ev(env)[0][4]))
    assert env['c'].get(f'/evidence/{eid}/preview').status_code == 404
    assert env['c'].get('/evidence/99999/preview').status_code == 404


def test_review_approve_reject_and_control_status(env):
    _up(env, 'ctx_4_1.pdf', title='A')
    _up(env, 'neg_blank_template.pdf', title='B')
    a, b = [x[0] for x in _ev(env)]
    env['c'].post(f'/evidence/{a}/review', data=dict(action='approve'))
    env['c'].post(f'/evidence/{b}/review', data=dict(action='reject', review_notes='blank template'))
    st = {x[0]: x[2] for x in _ev(env)}
    assert st == {a: 'Approved', b: 'Rejected'}
    env['c'].post(f'/evidence/{a}/review', data=dict(action='bogus'))
    assert {x[0]: x[2] for x in _ev(env)}[a] == 'Approved'


def test_accept_ai_only_for_clear_verdicts(env):
    from app.models import db, Evidence
    _up(env, 'ctx_4_1.pdf', title='A')
    _up(env, 'neg_vague_screenshot.png', title='B')
    a, b = [x[0] for x in _ev(env)]
    with env['app'].app_context():
        Evidence.query.get(a).ai_suggested_status = 'Approved'
        Evidence.query.get(b).ai_suggested_status = 'Needs Human Review'
        db.session.commit()
    env['c'].post(f'/evidence/{a}/review', data=dict(action='accept_ai'))
    env['c'].post(f'/evidence/{b}/review', data=dict(action='accept_ai'))
    st = {x[0]: x[2] for x in _ev(env)}
    assert st == {a: 'Approved', b: 'Pending Review'}


def test_gap_state_roundtrip(env):
    from app.models import db, Evidence
    _up(env, 'ctx_4_1.pdf')
    eid = _ev(env)[0][0]
    with env['app'].app_context():
        Evidence.query.get(eid).ai_gaps = json.dumps([{'gap': 'no approver', 'suggestion': 'add', 'state': 'open'}])
        db.session.commit()
    env['c'].post(f'/evidence/{eid}/gap/0', data=dict(state='done'))
    with env['app'].app_context():
        assert Evidence.query.get(eid).gaps[0]['state'] == 'done'


def test_delete_removes_file_and_cross_tenant_delete_blocked(env, app):
    _up(env, 'ctx_4_1.pdf')
    eid, path = _ev(env)[0][0], _ev(env)[0][4]
    other, uo = _org(app, 'Other', '@o.test')
    c2 = app.test_client(); _login(c2, uo, other)
    assert c2.post(f'/evidence/{eid}/delete').status_code == 404
    assert len(_ev(env)) == 1
    env['c'].post(f'/evidence/{eid}/delete')
    assert _ev(env) == [] and not os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], path))


def test_viewer_cannot_review_or_upload(env, app):
    from app.models import db, OrganizationMembership
    _up(env, 'ctx_4_1.pdf')
    eid = _ev(env)[0][0]
    with app.app_context():
        m = OrganizationMembership.query.filter_by(user_id=env['uid']).first()
        m.role = 'Viewer'
        db.session.commit()
    env['c'].post(f'/evidence/{eid}/review', data=dict(action='approve'))
    _up(env, 'scope_4_3.docx')
    assert [x[2] for x in _ev(env)] == ['Pending Review'] and len(_ev(env)) == 1


def test_jpg_image_upload_preview_and_download(env):
    gen.build_images(str(env['files'] / 'img'))
    body = open(env['files'] / 'img' / 'okta_people_a516.jpg', 'rb').read()
    _up(env, 'okta_people_a516.jpg', content=body)
    eid = _ev(env)[0][0]
    r = env['c'].get(f'/evidence/{eid}/preview')
    assert r.status_code == 200 and r.mimetype == 'image/jpeg' and r.data == body
    d = env['c'].get(f'/evidence/{eid}/preview?download=1')
    assert d.status_code == 200 and 'attachment' in d.headers['Content-Disposition'] and d.data == body


def test_details_json_and_tenant_isolation(env, app):
    _up(env, 'ctx_4_1.pdf', title='Ctx', extra={'map_controls': [str(env['cids'][1])], 'audit_period_start': '2026-01-01'})
    eid = _ev(env)[0][0]
    j = env['c'].get(f'/evidence/{eid}/details').get_json()
    assert j['title'] == 'Ctx' and j['status'] == 'Pending Review' and j['ai']['gap_label'] == 'Not Evaluated'
    assert sorted(c['code'] for c in j['controls']) == ['C1', 'C2'] and j['period'][0] == '2026-01-01'
    other, uo = _org(app, 'Other', '@o.test')
    c2 = app.test_client(); _login(c2, uo, other)
    assert c2.get(f'/evidence/{eid}/details').status_code == 404
    assert app.test_client().get(f'/evidence/{eid}/details').status_code in (301, 302, 401)


def test_details_gap_labels(env):
    from app.models import db, Evidence
    from datetime import datetime
    _up(env, 'ctx_4_1.pdf')
    eid = _ev(env)[0][0]
    with env['app'].app_context():
        e = db.session.get(Evidence, eid)
        e.ai_reviewed_at, e.ai_suggested_status = datetime.utcnow(), 'Approved'
        db.session.commit()
    assert env['c'].get(f'/evidence/{eid}/details').get_json()['ai']['gap_label'] == 'No Gaps'
    with env['app'].app_context():
        db.session.get(Evidence, eid).ai_gaps = json.dumps([{'gap': 'x', 'suggestion': 'y', 'state': 'open'}])
        db.session.commit()
    assert env['c'].get(f'/evidence/{eid}/details').get_json()['ai']['gap_label'] == 'Gaps Detected'


def test_control_page_renders_split_viewer(env):
    _up(env, 'ctx_4_1.pdf')
    h = env['c'].get(f"/compliance/{env['fw']}/control/{env['cids'][0]}").get_data(as_text=True)
    assert 'id="evDetails"' in h and 'id="evPrev"' in h and 'id="evDownload"' in h and 'class="ev-preview"' in h
