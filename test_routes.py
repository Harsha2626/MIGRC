import os
import tempfile

import pytest


@pytest.fixture
def app():
    """Create the app against a throwaway sqlite file so tests never touch migrc.db."""
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


@pytest.fixture
def client(app):
    return app.test_client()


def test_create_app_succeeds(app):
    assert app is not None


def test_login_page_returns_200(client):
    resp = client.get('/login')
    assert resp.status_code == 200


def test_trust_center_returns_200(client):
    resp = client.get('/trust-center')
    assert resp.status_code == 200


def test_dashboard_requires_login(client):
    resp = client.get('/')
    assert resp.status_code in (302, 401)
