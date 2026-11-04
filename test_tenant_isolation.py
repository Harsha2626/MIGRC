import os
import tempfile

import pytest


@pytest.fixture
def app():
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    os.environ['DATABASE_URL'] = 'sqlite:///' + db_path
    os.environ['FLASK_ENV'] = 'development'

    from app import create_app
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False

    yield flask_app

    from app.models import db
    with flask_app.app_context():
        db.session.remove()
        db.engine.dispose()
    from app.routes import auth
    auth._failed_logins.clear()
    os.environ.pop('DATABASE_URL', None)
    os.environ.pop('FLASK_ENV', None)
    os.remove(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


def _org(app, name, email):
    import uuid
    u = uuid.uuid4().hex[:8]
    name, email = f'{name}{u}', f'{u}{email}'
    from app.models import db, Organization, User, OrganizationMembership
    with app.app_context():
        org = Organization(name=name, slug=name.lower())
        db.session.add(org)
        db.session.flush()
        user = User(email=email, name=name + ' Admin', role='Admin')
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()
        db.session.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role='Admin'))
        db.session.commit()
        return org.id, user.id


def _shared_fw(app, name='ISO T', n=2):
    from app.models import db, Framework, Control
    with app.app_context():
        fw = Framework(name=name, description='d', category='Security', icon='shield')
        db.session.add(fw)
        db.session.flush()
        ids = []
        for i in range(n):
            c = Control(code=f'C{i+1}', title=f'Control {i+1}', description='d', category='G',
                        framework_id=fw.id, test_criteria='t', evidence_requirement='e')
            db.session.add(c)
            db.session.flush()
            ids.append(c.id)
        db.session.commit()
        return fw.id, ids


def _adopt(app, org_id, fw_id):
    from app.models import db, OrganizationFramework
    with app.app_context():
        db.session.add(OrganizationFramework(organization_id=org_id, framework_id=fw_id))
        db.session.commit()


def _evidence(app, org_id, control_id, title):
    from app.models import db, Evidence, EvidenceMapping
    with app.app_context():
        ev = Evidence(organization_id=org_id, title=title, file_name='f.pdf')
        db.session.add(ev)
        db.session.flush()
        db.session.add(EvidenceMapping(evidence_id=ev.id, control_id=control_id))
        db.session.commit()
        return ev.id


def _login(client, user_id, org_id):
    with client.session_transaction() as s:
        s['_user_id'] = str(user_id)
        s['_fresh'] = True
        s['current_org_id'] = org_id


def test_control_detail_hides_other_orgs_evidence(app, client):
    a, ua = _org(app, 'OrgA', 'a@x.test')
    b, ub = _org(app, 'OrgB', 'b@x.test')
    fw, cids = _shared_fw(app)
    _adopt(app, a, fw)
    _adopt(app, b, fw)
    _evidence(app, a, cids[0], 'SECRET-A-EVIDENCE')
    _evidence(app, b, cids[0], 'B-OWN-EVIDENCE')

    _login(client, ub, b)
    html = client.get(f'/compliance/{fw}/control/{cids[0]}').get_data(as_text=True)
    assert 'B-OWN-EVIDENCE' in html
    assert 'SECRET-A-EVIDENCE' not in html


def test_audit_detail_hides_other_orgs_evidence(app, client):
    from app.models import db, Audit, AuditEvidence
    a, ua = _org(app, 'OrgA', 'a@x.test')
    b, ub = _org(app, 'OrgB', 'b@x.test')
    fw, cids = _shared_fw(app)
    _adopt(app, a, fw)
    _adopt(app, b, fw)
    _evidence(app, a, cids[0], 'SECRET-A-EVIDENCE')
    _evidence(app, b, cids[0], 'B-OWN-EVIDENCE')
    with app.app_context():
        audit = Audit(organization_id=b, name='B audit')
        db.session.add(audit)
        db.session.flush()
        db.session.add(AuditEvidence(audit_id=audit.id, control_id=cids[0]))
        db.session.commit()
        audit_id = audit.id

    _login(client, ub, b)
    html = client.get(f'/audits/{audit_id}').get_data(as_text=True)
    assert 'B-OWN-EVIDENCE' in html
    assert 'SECRET-A-EVIDENCE' not in html


def test_upload_rejects_foreign_or_invisible_map_control_ids(app, client):
    import io
    from app.models import EvidenceMapping
    a, ua = _org(app, 'OrgA', 'a@x.test')
    b, ub = _org(app, 'OrgB', 'b@x.test')
    fw, cids = _shared_fw(app, 'Visible')
    hidden_fw, hidden_cids = _shared_fw(app, 'NotAdopted')  # shared, but B never adopted it
    _adopt(app, b, fw)

    _login(client, ub, b)
    resp = client.post(f'/compliance/{fw}/control/{cids[0]}/upload', data={
        'title': 'Doc', 'file': (io.BytesIO(b'hello'), 'doc.pdf'),
        'map_controls': [str(cids[1]), str(hidden_cids[0])],
    }, content_type='multipart/form-data')
    assert resp.status_code in (200, 302)
    with app.app_context():
        mapped = {m.control_id for m in EvidenceMapping.query.all()}
    assert cids[0] in mapped and cids[1] in mapped
    assert hidden_cids[0] not in mapped


def test_csv_export_neutralises_formulas():
    from app.services.csv_export import csv_response
    resp = csv_response('x.csv', ['=h'], [['=1+1', '+cmd', '-2', '@SUM(A1)', '\tx', 'safe', 5]])
    lines = resp.get_data(as_text=True).splitlines()
    assert lines[0] == "'=h"
    assert lines[1].startswith("'=1+1,'+cmd,'-2,'@SUM(A1),'\tx,safe,5")


def test_login_rate_limit_triggers(app, client):
    _, uid = _org(app, 'OrgA', 'a@x.test')
    from app.models import User
    with app.app_context():
        email = User.query.get(uid).email
    app.config['LOGIN_MAX_ATTEMPTS'] = 3
    for _ in range(3):
        r = client.post('/login', data={'email': email, 'password': 'wrong'})
        assert r.status_code == 200
    r = client.post('/login', data={'email': email, 'password': 'password123'})
    assert r.status_code == 429


def test_policy_assignees_restricted_to_org_members(app, client):
    from app.models import db, Policy
    a, ua = _org(app, 'OrgA', 'a@x.test')
    b, ub = _org(app, 'OrgB', 'b@x.test')
    with app.app_context():
        p = Policy(organization_id=a, name='P')
        db.session.add(p)
        db.session.commit()
        pid = p.id
    _login(client, ua, a)
    client.post(f'/policies/{pid}/assignees', data={'user_ids': [str(ua), str(ub)]})
    with app.app_context():
        assert {u.id for u in Policy.query.get(pid).assignees} == {ua}
