import os
import tempfile
import uuid

import pytest


@pytest.fixture
def app():
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    os.environ['DATABASE_URL'] = 'sqlite:///' + db_path
    os.environ['FLASK_ENV'] = 'development'

    from app import create_app
    from app.routes.incidents import incidents_bp
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    if 'incidents' not in flask_app.blueprints:
        flask_app.register_blueprint(incidents_bp)

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


def _org(app, name, role='Admin'):
    u = uuid.uuid4().hex[:8]
    from app.models import db, Organization, User, OrganizationMembership
    with app.app_context():
        org = Organization(name=f'{name}{u}', slug=f'{name.lower()}{u}')
        db.session.add(org)
        db.session.flush()
        user = User(email=f'{u}@x.test', name=f'{name} User', role=role)
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()
        db.session.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role=role))
        db.session.commit()
        return org.id, user.id


def _login(client, user_id, org_id):
    with client.session_transaction() as s:
        s['_user_id'] = str(user_id)
        s['_fresh'] = True
        s['current_org_id'] = org_id


def _make(app, org_id, user_id, title='Phish on finance', severity='High'):
    from app.models import db, Incident
    with app.app_context():
        inc = Incident(organization_id=org_id, title=title, severity=severity, status='Detected',
                       reported_by_id=user_id, owner_id=user_id)
        db.session.add(inc)
        db.session.commit()
        return inc.id


def _get(app, iid):
    from app.models import Incident
    return Incident.query.get(iid)


def test_create_and_list_and_detail(app, client):
    a, ua = _org(app, 'OrgA')
    _login(client, ua, a)
    r = client.post('/incidents/new', data={'title': 'Ransomware on FS01', 'severity': 'Critical',
                                           'category': 'Malware', 'owner_id': str(ua),
                                           'detected_at': '2026-01-02T03:04'})
    assert r.status_code == 302
    html = client.get('/incidents').get_data(as_text=True)
    assert 'Ransomware on FS01' in html
    with app.app_context():
        from app.models import Incident
        inc = Incident.query.filter_by(organization_id=a).one()
        assert inc.status == 'Detected' and len(inc.timeline) == 1
        iid = inc.id
    d = client.get(f'/incidents/{iid}').get_data(as_text=True)
    assert 'Ransomware on FS01' in d and 'Response progress' in d


def test_create_validation(app, client):
    a, ua = _org(app, 'OrgA')
    b, ub = _org(app, 'OrgB')
    _login(client, ua, a)
    assert client.post('/incidents/new', data={'title': '', 'severity': 'High'}).status_code == 400
    assert client.post('/incidents/new', data={'title': 'x', 'severity': 'Bogus'}).status_code == 400
    # owner from another org rejected
    assert client.post('/incidents/new', data={'title': 'x', 'severity': 'High', 'owner_id': str(ub)}).status_code == 400


def test_edit(app, client):
    a, ua = _org(app, 'OrgA')
    iid = _make(app, a, ua)
    _login(client, ua, a)
    r = client.post(f'/incidents/{iid}/edit', data={'title': 'Renamed', 'severity': 'Low'})
    assert r.status_code == 302
    with app.app_context():
        inc = _get(app, iid)
        assert inc.title == 'Renamed' and inc.severity == 'Low'


def test_status_flow_and_close(app, client):
    from app.models import Incident, Notification
    a, ua = _org(app, 'OrgA')
    iid = _make(app, a, ua)
    _login(client, ua, a)
    # skipping steps rejected
    client.post(f'/incidents/{iid}/status', data={'status': 'Contained'})
    with app.app_context():
        assert _get(app, iid).status == 'Detected'
    for st in ['Triaged', 'Contained', 'Eradicated', 'Recovered']:
        client.post(f'/incidents/{iid}/status', data={'status': st})
        with app.app_context():
            assert _get(app, iid).status == st
    # closing needs resolution summary
    client.post(f'/incidents/{iid}/status', data={'status': 'Closed'})
    with app.app_context():
        assert _get(app, iid).status == 'Recovered'
    client.post(f'/incidents/{iid}/status', data={'status': 'Closed', 'resolution_summary': 'Reimaged'})
    with app.app_context():
        inc = _get(app, iid)
        assert inc.status == 'Closed' and inc.closed_at is not None and inc.resolution_hours is not None
        assert len(inc.timeline) == 5  # 5 transitions (no creation entry via _make)
    # reopen
    client.post(f'/incidents/{iid}/status', data={'status': 'Recovered'})
    with app.app_context():
        inc = _get(app, iid)
        assert inc.status == 'Recovered' and inc.closed_at is None


def test_status_notifies_other_owner(app, client):
    from app.models import db, User, OrganizationMembership, Notification
    a, ua = _org(app, 'OrgA')
    with app.app_context():
        u2 = User(email=f'{uuid.uuid4().hex[:8]}@x.test', name='Owner Two', role='Viewer')
        u2.set_password('password123')
        db.session.add(u2)
        db.session.flush()
        db.session.add(OrganizationMembership(user_id=u2.id, organization_id=a, role='Viewer'))
        db.session.commit()
        u2id = u2.id
    _login(client, ua, a)
    client.post('/incidents/new', data={'title': 'Assigned', 'severity': 'High', 'owner_id': str(u2id)})
    with app.app_context():
        n = Notification.query.filter_by(user_id=u2id, type='incident').all()
        assert len(n) == 1


def test_notes_and_review(app, client):
    a, ua = _org(app, 'OrgA')
    iid = _make(app, a, ua)
    _login(client, ua, a)
    client.post(f'/incidents/{iid}/notes', data={'body': 'Isolated host', 'entry_type': 'action'})
    client.post(f'/incidents/{iid}/review', data={'lessons_learned': 'Patch faster', 'follow_up_actions': 'Deploy EDR',
                                                  'mark_complete': '1'})
    with app.app_context():
        inc = _get(app, iid)
        assert any(e.body == 'Isolated host' and e.entry_type == 'action' for e in inc.timeline)
        assert inc.lessons_learned == 'Patch faster' and inc.review_completed_at is not None
    assert 'Isolated host' in client.get(f'/incidents/{iid}').get_data(as_text=True)


def test_link_controls_and_risks(app, client):
    from app.models import db, Framework, Control, OrganizationFramework, Risk
    a, ua = _org(app, 'OrgA')
    iid = _make(app, a, ua)
    with app.app_context():
        fw = Framework(name='FWV', description='d', category='Security', icon='shield')
        fw2 = Framework(name='FWHidden', description='d', category='Security', icon='shield')
        db.session.add_all([fw, fw2])
        db.session.flush()
        db.session.add(OrganizationFramework(organization_id=a, framework_id=fw.id))
        c1 = Control(code='V1', title='vis', description='d', category='G', framework_id=fw.id, test_criteria='t', evidence_requirement='e')
        c2 = Control(code='H1', title='hid', description='d', category='G', framework_id=fw2.id, test_criteria='t', evidence_requirement='e')
        db.session.add_all([c1, c2])
        r_own = Risk(organization_id=a, title='own risk', score=3)
        db.session.add(r_own)
        db.session.commit()
        c1id, c2id, rid = c1.id, c2.id, r_own.id
    b, ub = _org(app, 'OrgB')
    with app.app_context():
        rb = Risk(organization_id=b, title='foreign risk', score=3)
        db.session.add(rb)
        db.session.commit()
        rbid = rb.id
    _login(client, ua, a)
    client.post(f'/incidents/{iid}/controls/link', data={'control_ids': [str(c1id), str(c2id)]})
    client.post(f'/incidents/{iid}/risks/link', data={'risk_ids': [str(rid), str(rbid)]})
    with app.app_context():
        inc = _get(app, iid)
        assert [c.id for c in inc.controls] == [c1id]
        assert [r.id for r in inc.risks] == [rid]
    client.post(f'/incidents/{iid}/controls/{c1id}/unlink')
    client.post(f'/incidents/{iid}/risks/{rid}/unlink')
    with app.app_context():
        inc = _get(app, iid)
        assert inc.controls == [] and inc.risks == []


def test_csv_export_and_filters(app, client):
    a, ua = _org(app, 'OrgA')
    b, ub = _org(app, 'OrgB')
    _make(app, a, ua, title='=HYPERLINK("x")', severity='Critical')
    _make(app, a, ua, title='Minor thing', severity='Low')
    _make(app, b, ub, title='B-SECRET', severity='Critical')
    _login(client, ua, a)
    r = client.get('/incidents/export.csv')
    assert r.status_code == 200 and r.mimetype == 'text/csv'
    body = r.get_data(as_text=True)
    assert "'=HYPERLINK" in body and 'Minor thing' in body and 'B-SECRET' not in body
    body = client.get('/incidents/export.csv?severity=Low').get_data(as_text=True)
    assert 'Minor thing' in body and 'HYPERLINK' not in body
    html = client.get('/incidents?severity=Critical').get_data(as_text=True)
    assert 'Minor thing' not in html and 'B-SECRET' not in html


def test_org_isolation(app, client):
    from app.models import Incident
    a, ua = _org(app, 'OrgA')
    b, ub = _org(app, 'OrgB')
    iid = _make(app, a, ua, title='A-SECRET')
    _login(client, ub, b)
    assert 'A-SECRET' not in client.get('/incidents').get_data(as_text=True)
    assert client.get(f'/incidents/{iid}').status_code == 404
    assert client.get(f'/incidents/{iid}/edit').status_code == 404
    posts = [
        (f'/incidents/{iid}/edit', {'title': 'pwn', 'severity': 'Low'}),
        (f'/incidents/{iid}/status', {'status': 'Triaged'}),
        (f'/incidents/{iid}/notes', {'body': 'pwn'}),
        (f'/incidents/{iid}/controls/link', {'control_ids': ['1']}),
        (f'/incidents/{iid}/risks/link', {'risk_ids': ['1']}),
        (f'/incidents/{iid}/review', {'lessons_learned': 'pwn'}),
        (f'/incidents/{iid}/delete', {}),
    ]
    for url, data in posts:
        assert client.post(url, data=data).status_code == 404, url
    with app.app_context():
        inc = Incident.query.get(iid)
        assert inc is not None and inc.title == 'A-SECRET' and inc.status == 'Detected' and not inc.timeline


def test_permissions(app, client):
    a, viewer = _org(app, 'OrgA', role='Viewer')
    iid = _make(app, a, viewer)
    _login(client, viewer, a)
    assert client.get(f'/incidents/{iid}').status_code == 200  # read allowed
    client.post('/incidents/new', data={'title': 'nope', 'severity': 'High'})
    client.post(f'/incidents/{iid}/status', data={'status': 'Triaged'})
    client.post(f'/incidents/{iid}/delete')
    from app.models import Incident
    with app.app_context():
        assert Incident.query.filter_by(organization_id=a).count() == 1
        assert _get(app, iid).status == 'Detected'


def test_delete_requires_delete_permission_and_works(app, client):
    from app.models import Incident
    a, ua = _org(app, 'OrgA')
    iid = _make(app, a, ua)
    _login(client, ua, a)
    client.post(f'/incidents/{iid}/delete')
    with app.app_context():
        assert Incident.query.filter_by(organization_id=a).count() == 0


def test_login_required(app, client):
    assert client.get('/incidents').status_code == 302
    assert client.post('/incidents/1/delete').status_code == 302
