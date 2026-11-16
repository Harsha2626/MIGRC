import base64, json, os, tempfile
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture
def client():
    path = os.path.join(tempfile.mkdtemp(), 't.db')
    os.environ['DATABASE_URL'] = 'sqlite:///' + path
    os.environ.update(ENTRA_CLIENT_ID='cid', ENTRA_CLIENT_SECRET='sec', ENTRA_REDIRECT_URI='http://x/cb')
    from app import create_app
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    yield app
    for k in ('DATABASE_URL', 'ENTRA_CLIENT_ID', 'ENTRA_CLIENT_SECRET', 'ENTRA_REDIRECT_URI'):
        os.environ.pop(k, None)


def _jwt(claims):
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip('=')
    return f'{b({"alg":"none"})}.{b(claims)}.sig'


def test_claims_and_token_encryption(client):
    from app.routes.entra_oauth import _claims
    from app.services.crypto import encrypt, decrypt
    assert _claims(_jwt({'tid': 'T1', 'preferred_username': 'a@b.com'}))['tid'] == 'T1'
    assert encrypt('x').startswith('enc:v1:') and decrypt(encrypt('x')) == 'x'


def test_sync_upserts_and_skips_guests(client):
    from datetime import datetime, timedelta
    from app.models import db, Organization, User, EntraConnection, Employee
    from app.services.crypto import encrypt
    with client.app_context():
        org = Organization(name='O', slug='o'); db.session.add(org); db.session.flush()
        db.session.add(EntraConnection(organization_id=org.id, tenant_id='T', account='a@b.com',
                                       access_token=encrypt('at'), refresh_token=encrypt('rt'),
                                       token_expiry=datetime.utcnow() + timedelta(hours=1)))
        db.session.commit()
        page = {'value': [
            {'displayName': 'A', 'mail': 'A@x.com', 'accountEnabled': True, 'userType': 'Member'},
            {'displayName': 'G', 'mail': 'g@ext.com', 'userType': 'Guest'},
            {'displayName': 'D', 'userPrincipalName': 'd@x.com', 'accountEnabled': False, 'userType': 'Member'}]}
        resp = MagicMock(); resp.json.return_value = page
        with patch('app.routes.entra_oauth.requests.get', return_value=resp) as get:
            from app.routes import entra_oauth as m
            from flask import g
            with client.test_request_context('/'):
                g.current_org = org
                from flask_login import login_user
                u = User.query.first()
                # call view body without auth decorators
                fn = m.sync_employees.__wrapped__
                while hasattr(fn, '__wrapped__'): fn = fn.__wrapped__
                fn()
            assert get.call_args.kwargs['headers']['Authorization'] == 'Bearer at'
        emps = {e.email: e for e in Employee.query.filter_by(organization_id=org.id)}
        assert set(emps) == {'a@x.com', 'd@x.com'} and emps['d@x.com'].status == 'Suspended'
