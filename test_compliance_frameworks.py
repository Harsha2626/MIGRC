import os
import tempfile

import pytest


@pytest.fixture
def app():
    """Create the app against a throwaway sqlite file so tests never touch migrc.db
    or the real (Neon Postgres) DATABASE_URL."""
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

    os.environ.pop('DATABASE_URL', None)
    os.environ.pop('FLASK_ENV', None)
    os.remove(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


def _make_org_and_admin(app, org_name='Acme', email='admin@acme.test'):
    """Creates an Organization + a User who is an Admin member of it. Returns (org_id, user_id)."""
    from app.models import db, Organization, User, OrganizationMembership

    with app.app_context():
        org = Organization(name=org_name, slug=org_name.lower().replace(' ', '-'))
        db.session.add(org)
        db.session.flush()

        user = User(email=email, name='Admin User', role='Admin')
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()

        db.session.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role='Admin'))
        db.session.commit()

        return org.id, user.id


def _make_shared_framework(app, name='ISO 9999', num_controls=2):
    """Creates a shared-library Framework (organization_id=None) with a couple of Controls."""
    from app.models import db, Framework, Control

    with app.app_context():
        fw = Framework(name=name, description='Test shared framework', category='Security', icon='shield')
        db.session.add(fw)
        db.session.flush()

        for i in range(num_controls):
            db.session.add(Control(
                code=f'C{i+1}', title=f'Control {i+1}', description='desc',
                category='General', framework_id=fw.id,
                test_criteria='criteria', evidence_requirement='evidence',
            ))
        db.session.commit()
        return fw.id


def _login(client, user_id, org_id=None):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True
        if org_id is not None:
            sess['current_org_id'] = org_id


# ---------------------------------------------------------------------------
# Framework.visible_to / Framework.library
# ---------------------------------------------------------------------------

def test_new_org_has_no_visible_frameworks(app):
    from app.models import Framework

    org_id, _ = _make_org_and_admin(app, org_name='New Org', email='new@acme.test')
    with app.app_context():
        assert Framework.visible_to(org_id).all() == []


def test_library_includes_unadopted_and_excludes_adopted(app):
    from app.models import db, Framework, OrganizationFramework

    org_id, _ = _make_org_and_admin(app, org_name='Library Org', email='library@acme.test')
    fw_id = _make_shared_framework(app, name='ISO 9999')

    with app.app_context():
        library_ids = [f.id for f in Framework.library(org_id).all()]
        assert fw_id in library_ids
        assert Framework.visible_to(org_id).all() == []

        db.session.add(OrganizationFramework(organization_id=org_id, framework_id=fw_id))
        db.session.commit()

        library_ids_after = [f.id for f in Framework.library(org_id).all()]
        assert fw_id not in library_ids_after
        visible_ids_after = [f.id for f in Framework.visible_to(org_id).all()]
        assert fw_id in visible_ids_after


# ---------------------------------------------------------------------------
# POST /compliance/add - adopting a shared framework
# ---------------------------------------------------------------------------

def test_add_framework_adopts_shared_framework(client, app):
    from app.models import OrganizationFramework, Framework

    org_id, user_id = _make_org_and_admin(app, org_name='Adopt Org', email='adopt@acme.test')
    fw_id = _make_shared_framework(app, name='ISO 9001-Test')
    _login(client, user_id, org_id)

    resp = client.post('/compliance/add', data={'framework_id': str(fw_id)}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'ISO 9001-Test' in resp.data

    with app.app_context():
        adoption = OrganizationFramework.query.filter_by(organization_id=org_id, framework_id=fw_id).first()
        assert adoption is not None
        assert fw_id in [f.id for f in Framework.visible_to(org_id).all()]


def test_add_framework_rejects_duplicate_adoption(client, app):
    from app.models import OrganizationFramework

    org_id, user_id = _make_org_and_admin(app, org_name='Dup Org', email='dup@acme.test')
    fw_id = _make_shared_framework(app, name='Dup Framework')
    _login(client, user_id, org_id)

    resp1 = client.post('/compliance/add', data={'framework_id': str(fw_id)}, follow_redirects=True)
    assert resp1.status_code == 200

    resp2 = client.post('/compliance/add', data={'framework_id': str(fw_id)}, follow_redirects=True)
    assert resp2.status_code == 200
    assert b'already active' in resp2.data

    with app.app_context():
        count = OrganizationFramework.query.filter_by(organization_id=org_id, framework_id=fw_id).count()
        assert count == 1


def test_add_framework_custom_creates_private_framework(client, app):
    from app.models import Framework

    org_id, user_id = _make_org_and_admin(app, org_name='Custom Org', email='custom@acme.test')
    _login(client, user_id, org_id)

    resp = client.post('/compliance/add', data={
        'framework_id': '__custom__',
        'custom_name': 'My Internal Baseline',
        'category': 'Security',
        'owner': 'Jane Doe',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'My Internal Baseline' in resp.data

    with app.app_context():
        fw = Framework.query.filter_by(organization_id=org_id, name='My Internal Baseline').first()
        assert fw is not None
        assert fw.organization_id == org_id
        assert fw.id in [f.id for f in Framework.visible_to(org_id).all()]


# ---------------------------------------------------------------------------
# POST /compliance/<id>/delete
# ---------------------------------------------------------------------------

def test_delete_shared_framework_removes_adoption_not_the_framework(client, app):
    from app.models import db, Framework, Control, OrganizationFramework

    org_id, user_id = _make_org_and_admin(app, org_name='Remove Shared Org', email='removeshared@acme.test')
    fw_id = _make_shared_framework(app, name='Removable Shared FW')
    with app.app_context():
        db.session.add(OrganizationFramework(organization_id=org_id, framework_id=fw_id))
        db.session.commit()

    _login(client, user_id, org_id)
    resp = client.post(f'/compliance/{fw_id}/delete', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        assert OrganizationFramework.query.filter_by(organization_id=org_id, framework_id=fw_id).first() is None
        # The shared framework and its controls must still exist.
        assert Framework.query.get(fw_id) is not None
        assert Control.query.filter_by(framework_id=fw_id).count() == 2


def test_delete_custom_framework_deletes_it(client, app):
    from app.models import db, Framework

    org_id, user_id = _make_org_and_admin(app, org_name='Remove Custom Org', email='removecustom@acme.test')
    with app.app_context():
        fw = Framework(organization_id=org_id, name='Private FW', category='Security', icon='shield')
        db.session.add(fw)
        db.session.commit()
        fw_id = fw.id

    _login(client, user_id, org_id)
    resp = client.post(f'/compliance/{fw_id}/delete', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        assert Framework.query.get(fw_id) is None


# ---------------------------------------------------------------------------
# Setup wizard: choose_frameworks auto-completion
# ---------------------------------------------------------------------------

def test_choose_frameworks_task_false_until_adopted(app):
    from app.routes.setup import _auto_completion
    from app.models import db, Organization, OrganizationFramework

    org_id, _ = _make_org_and_admin(app, org_name='Setup Org', email='setup@acme.test')
    fw_id = _make_shared_framework(app, name='Setup Framework')

    with app.app_context():
        org = Organization.query.get(org_id)
        assert _auto_completion(org)['choose_frameworks'] is False

        db.session.add(OrganizationFramework(organization_id=org_id, framework_id=fw_id))
        db.session.commit()

        org = Organization.query.get(org_id)
        assert _auto_completion(org)['choose_frameworks'] is True


def test_choose_frameworks_task_true_for_private_framework(app):
    from app.routes.setup import _auto_completion
    from app.models import db, Organization, Framework

    org_id, _ = _make_org_and_admin(app, org_name='Setup Org 2', email='setup2@acme.test')

    with app.app_context():
        org = Organization.query.get(org_id)
        assert _auto_completion(org)['choose_frameworks'] is False

        db.session.add(Framework(organization_id=org_id, name='Private FW 2', category='Security', icon='shield'))
        db.session.commit()

        org = Organization.query.get(org_id)
        assert _auto_completion(org)['choose_frameworks'] is True
