import os
import tempfile
from datetime import date, timedelta

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
    yield flask_app

    from app.models import db
    with flask_app.app_context():
        db.session.remove()
        db.engine.dispose()
    os.environ.pop('DATABASE_URL', None)
    os.environ.pop('FLASK_ENV', None)
    os.remove(db_path)


def _make_org(slug, policy_name):
    from app.models import db, Organization, User, OrganizationMembership, Policy, Framework, OrganizationFramework
    org = Organization(name=slug.upper(), slug=slug)
    user = User(email=f'{slug}@example.com', password_hash='x', name=slug)
    db.session.add_all([org, user])
    db.session.flush()
    db.session.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role='Admin'))
    due = (date.today() + timedelta(days=3)).isoformat()
    db.session.add(Policy(organization_id=org.id, name=policy_name, status='Published', next_review=due))
    fw = Framework(name=f'FW-{slug}', organization_id=org.id)
    db.session.add(fw)
    db.session.commit()
    return org.id, user.id


def test_daily_jobs_idempotent_and_isolated(app):
    from app.models import db, DashboardSnapshot, ComplianceSnapshot, Notification
    with app.app_context():
        a_id, a_user = _make_org('orga', 'Policy A')
        b_id, b_user = _make_org('orgb', 'Policy B')

    runner = app.test_cli_runner()
    r1 = runner.invoke(args=['run-daily-jobs'])
    assert r1.exit_code == 0, r1.output
    r2 = runner.invoke(args=['run-daily-jobs'])
    assert r2.exit_code == 0, r2.output
    assert ' 0 notifications created' in r2.output

    with app.app_context():
        for org_id, user_id, name, other_name in ((a_id, a_user, 'Policy A', 'Policy B'),
                                                   (b_id, b_user, 'Policy B', 'Policy A')):
            assert DashboardSnapshot.query.filter_by(organization_id=org_id, snapshot_date=date.today()).count() == 1
            assert ComplianceSnapshot.query.filter_by(organization_id=org_id).count() == 1
            notifs = Notification.query.filter_by(organization_id=org_id).all()
            assert len(notifs) == 1
            assert notifs[0].user_id == user_id
            assert name in notifs[0].title and other_name not in notifs[0].title
        # No cross-org leakage of framework snapshots
        a_fw_ids = {s.framework_id for s in ComplianceSnapshot.query.filter_by(organization_id=a_id)}
        b_fw_ids = {s.framework_id for s in ComplianceSnapshot.query.filter_by(organization_id=b_id)}
        assert not (a_fw_ids & b_fw_ids)


def test_on_demand_snapshot_after_cli_is_noop(app):
    from flask import g
    from app.models import db, Organization, DashboardSnapshot
    from app.services.snapshots import ensure_snapshots_for_today
    with app.app_context():
        org_id, _ = _make_org('orgc', 'Policy C')
    app.test_cli_runner().invoke(args=['run-daily-jobs'])
    with app.test_request_context():
        g.current_org = db.session.get(Organization, org_id)
        assert ensure_snapshots_for_today() == 0
        assert DashboardSnapshot.query.filter_by(organization_id=org_id).count() == 1


def test_overdue_and_evidence_notifications_dedupe(app):
    from app.models import db, Vendor, Evidence, Notification
    from datetime import datetime
    with app.app_context():
        org_id, _ = _make_org('orgd', 'Policy D')
        db.session.add(Vendor(organization_id=org_id, name='V1',
                              next_assessment=(date.today() - timedelta(days=2)).isoformat()))
        db.session.add(Evidence(organization_id=org_id, title='Old ev', status='Pending Review',
                                created_at=datetime.utcnow() - timedelta(days=30)))
        db.session.commit()
    runner = app.test_cli_runner()
    runner.invoke(args=['run-daily-jobs'])
    with app.app_context():
        first = Notification.query.filter_by(organization_id=org_id).count()
    assert first == 3  # policy due, vendor overdue, stale evidence
    runner.invoke(args=['run-daily-jobs'])
    with app.app_context():
        assert Notification.query.filter_by(organization_id=org_id).count() == first


def test_seed_and_status_commands(app):
    runner = app.test_cli_runner()
    r = runner.invoke(args=['seed-frameworks'])
    assert r.exit_code == 0, r.output
    r2 = runner.invoke(args=['seed-frameworks'])
    assert 'Added 0 frameworks' in r2.output
    r3 = runner.invoke(args=['jobs-status'])
    assert r3.exit_code == 0 and 'Shared framework library' in r3.output


def test_integrations_page_is_honest(app):
    client = app.test_client()
    with app.app_context():
        from app.models import db, User, Organization, OrganizationMembership
        from werkzeug.security import generate_password_hash
        org = Organization(name='O', slug='o')
        u = User(email='u@example.com', password_hash=generate_password_hash('pw'), name='U', role='Admin')
        db.session.add_all([org, u]); db.session.flush()
        db.session.add(OrganizationMembership(user_id=u.id, organization_id=org.id, role='Admin'))
        db.session.commit()
        uid = u.id
    with client.session_transaction() as s:
        s['_user_id'] = str(uid)
        s['_fresh'] = True
    html = client.get('/integrations').get_data(as_text=True)
    assert 'Planned' in html and 'coming soon' not in html
    assert 'Not connected' in html or 'Not configured' in html
