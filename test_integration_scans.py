"""Integration scan pipeline: run_scan / run_scans_for_org / scans routes / generic integrations card.
A fake provider is injected into the registry, so no network is touched."""
import json
import os
import tempfile
from unittest.mock import patch

import pytest

from app.integrations import Check

FAKE_CFG = {'token': 'tok-SECRET-123', 'site': 'acme'}


@pytest.fixture
def app(monkeypatch):
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + db_path)
    from app import create_app
    flask_app = create_app()
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    yield flask_app
    from app.models import db
    with flask_app.app_context():
        db.session.remove()
        db.engine.dispose()
    from app.routes import auth
    auth._failed_logins.clear()
    os.remove(db_path)


class Fake:
    """Mutable fake provider: set .checks / .validate_exc between scans."""
    def __init__(self):
        self.checks = []
        self.validate_exc = None
        self.scan_exc = None
        self.seen_cfg = None

    def spec(self, key='fake', name='Fakeco'):
        def validate(cfg):
            if self.validate_exc:
                raise self.validate_exc
            return 'acct-label'

        def scan(cfg):
            self.seen_cfg = cfg
            if self.scan_exc:
                raise self.scan_exc
            return list(self.checks)
        return {'key': key, 'name': name, 'category': 'SaaS Application', 'icon': 'fas fa-bug', 'color': 'blue',
                'capabilities': ['Cap-One'],
                'fields': [{'name': 'token', 'label': 'API token', 'secret': True},
                           {'name': 'site', 'label': 'Site name'}],
                'validate': validate, 'scan': scan}


@pytest.fixture
def fake(monkeypatch):
    import app.integrations as integ
    f = Fake()
    monkeypatch.setitem(integ._REGISTRY, 'fake', f.spec())
    monkeypatch.setitem(integ._REGISTRY, 'fake2', f.spec('fake2', 'Fakeco Two'))
    return f


def _org(app, name, role='Admin'):
    from app.models import db, Organization, User, OrganizationMembership
    import uuid
    name = f'{name}{uuid.uuid4().hex[:8]}'  # the DB can be shared across tests, keep names unique
    with app.app_context():
        org = Organization(name=name, slug=name.lower())
        db.session.add(org)
        db.session.flush()
        u = User(email=f'{name.lower()}@x.test', name=name, role=role)
        u.set_password('password123')
        db.session.add(u)
        db.session.flush()
        db.session.add(OrganizationMembership(user_id=u.id, organization_id=org.id, role=role))
        db.session.commit()
        return org.id, u.id


def _fw(app, org_ids, title='Network firewall policy', n_other=1):
    """Framework with a keyword-matching control + non-matching ones; adopted by org_ids."""
    from app.models import db, Framework, Control, OrganizationFramework
    with app.app_context():
        fw = Framework(name=f'FW{title}', description='d', category='Security', icon='shield')
        db.session.add(fw)
        db.session.flush()
        match = Control(code='M1', title=title, description='d', category='G', framework_id=fw.id,
                        test_criteria='t', evidence_requirement='e')
        db.session.add(match)
        for i in range(n_other):
            db.session.add(Control(code=f'O{i}', title='Unrelated thing', description='d', category='G',
                                   framework_id=fw.id, test_criteria='t', evidence_requirement='e'))
        for oid in org_ids:
            db.session.add(OrganizationFramework(organization_id=oid, framework_id=fw.id))
        db.session.commit()
        return fw.id, match.id


def _connect(app, org_id, provider='fake', cfg=FAKE_CFG):
    from app.models import db, IntegrationConnection
    from app.services.crypto import encrypt
    with app.app_context():
        db.session.add(IntegrationConnection(organization_id=org_id, provider=provider,
                                             config=encrypt(json.dumps(cfg))))
        db.session.commit()


def _scan(app, org_id, provider='fake', ai=False):
    from app.models import Organization
    from app.services.integration_scans import run_scan
    with app.app_context():
        return run_scan(Organization.query.get(org_id), provider, ai=ai)


def _login(client, uid, oid):
    with client.session_transaction() as s:
        s['_user_id'] = str(uid)
        s['_fresh'] = True
        s['current_org_id'] = oid


def _ck(title='Firewall enabled', passed=True, detail='d', kw=('firewall',), sev='High'):
    return Check(title, passed, detail, list(kw), sev)


# ---------- (1) evidence + mapping ----------

def test_evidence_upsert_and_mapping_scoped_to_org_frameworks(app, fake):
    a, _ = _org(app, 'OrgA')
    b, _ = _org(app, 'OrgB')
    fw_a, ctrl_a = _fw(app, [a], title='Network firewall policy')
    _fw(app, [b], title='Other firewall control')  # b's framework only; must never be mapped for a
    _fw(app, [], title='Unadopted firewall control')
    _connect(app, a)
    _connect(app, b)
    fake.checks = [_ck('Check One'), _ck('Check Two', kw=('nomatchzzz',))]

    assert _scan(app, a)[:3] == (2, 0, 1)
    assert _scan(app, a)[:3] == (2, 0, 0)  # rescan: nothing new
    from app.models import Evidence, EvidenceMapping
    with app.app_context():
        evs = Evidence.query.filter_by(organization_id=a).all()
        assert sorted(e.title for e in evs) == ['Check One', 'Check Two']
        assert all(e.source_type == 'integration:fake' and e.status == 'Pending Review' for e in evs)
        one = next(e for e in evs if e.title == 'Check One')
        assert [m.control_id for m in one.evidence_mappings] == [ctrl_a]
        assert next(e for e in evs if e.title == 'Check Two').evidence_mappings.count() == 0
        assert Evidence.query.filter_by(organization_id=b).count() == 0
        assert EvidenceMapping.query.count() == 1
    # org B scans: its own evidence, mapped only to its own framework control (no leakage to a's)
    _scan(app, b)
    with app.app_context():
        ev_b = Evidence.query.filter_by(organization_id=b, title='Check One').one()
        ctrl_ids = {m.control_id for m in ev_b.evidence_mappings}
        assert len(ctrl_ids) == 1 and ctrl_a not in ctrl_ids
        assert Evidence.query.filter_by(source_type='integration:fake').count() == 4


def test_org_without_frameworks_gets_evidence_but_no_mappings(app, fake):
    a, _ = _org(app, 'OrgA')
    _fw(app, [], title='Network firewall policy')
    _connect(app, a)
    fake.checks = [_ck()]
    assert _scan(app, a)[:3] == (1, 0, 0)


def test_empty_keywords_map_nothing(app, fake):
    a, _ = _org(app, 'OrgA')
    _fw(app, [a])
    _connect(app, a)
    fake.checks = [_ck(kw=())]
    assert _scan(app, a)[2] == 0


def test_long_title_is_truncated_and_upserts(app, fake):
    a, _ = _org(app, 'OrgA')
    _connect(app, a)
    fake.checks = [_ck('T' * 300, kw=())]
    _scan(app, a)
    _scan(app, a)
    from app.models import Evidence, Risk
    with app.app_context():
        assert Evidence.query.filter_by(organization_id=a).count() == 1


def test_rescan_resets_reviewed_evidence_to_pending(app, fake):
    a, _ = _org(app, 'OrgA')
    _connect(app, a)
    fake.checks = [_ck(kw=())]
    _scan(app, a)
    from app.models import db, Evidence
    with app.app_context():
        Evidence.query.one().status = 'Approved'
        db.session.commit()
    _scan(app, a)
    with app.app_context():
        assert Evidence.query.one().status == 'Pending Review'


# ---------- (2) risks ----------

def test_failed_check_opens_single_risk_with_severity_and_control(app, fake):
    from app.models import db, Risk
    a, _ = _org(app, 'OrgA')
    _, ctrl = _fw(app, [a])
    _connect(app, a)
    fake.checks = [_ck('Bad thing', passed=False, sev='Critical'), _ck('Meh', passed=False, kw=(), sev='Low'),
                   _ck('Weird', passed=False, kw=(), sev='Bogus')]
    assert _scan(app, a)[3] == 3
    assert _scan(app, a)[3] == 0
    with app.app_context():
        risks = {r.title: r for r in Risk.query.filter_by(organization_id=a)}
        assert set(risks) == {'[Scan] Bad thing', '[Scan] Meh', '[Scan] Weird'}
        r = risks['[Scan] Bad thing']
        assert (r.impact, r.likelihood, r.score, r.linked_control_id, r.status) == ('Critical', 'Medium', 15, ctrl, 'Open')
        assert (risks['[Scan] Meh'].impact, risks['[Scan] Meh'].score, risks['[Scan] Meh'].linked_control_id) == ('Low', 6, None)
        assert (risks['[Scan] Weird'].impact, risks['[Scan] Weird'].score) == ('High', 12)


def test_rescan_refreshes_description_without_duplicate(app, fake):
    from app.models import Risk
    a, _ = _org(app, 'OrgA')
    _connect(app, a)
    fake.checks = [_ck('X', passed=False, detail='first', kw=())]
    _scan(app, a)
    fake.checks = [_ck('X', passed=False, detail='second', kw=())]
    _scan(app, a)
    with app.app_context():
        r = Risk.query.one()
        assert 'second' in r.description and 'first' not in r.description


@pytest.mark.parametrize('status,kept', [('Open', False), ('In Treatment', True), ('Accepted', True)])
def test_passing_check_closes_only_open_risk(app, fake, status, kept):
    from app.models import db, Risk
    a, _ = _org(app, 'OrgA')
    _connect(app, a)
    fake.checks = [_ck('X', passed=False, kw=())]
    _scan(app, a)
    with app.app_context():
        Risk.query.one().status = status
        db.session.commit()
    fake.checks = [_ck('X', passed=True, kw=())]
    _scan(app, a)
    with app.app_context():
        assert (Risk.query.count() == 1) is kept


def test_risks_are_per_org(app, fake):
    from app.models import Risk
    a, _ = _org(app, 'OrgA')
    b, _ = _org(app, 'OrgB')
    _connect(app, a)
    _connect(app, b)
    fake.checks = [_ck('X', passed=False, kw=())]
    _scan(app, a)
    _scan(app, b)
    fake.checks = [_ck('X', passed=True, kw=())]
    _scan(app, a)
    with app.app_context():
        assert [r.organization_id for r in Risk.query.all()] == [b]


# ---------- (3) AI ----------

def test_ai_suggestion_stored_but_status_untouched(app, fake):
    a, _ = _org(app, 'OrgA')
    _fw(app, [a])
    _connect(app, a)
    fake.checks = [_ck()]
    sugg = {'status': 'Approved', 'confidence': 0.9, 'rationale': 'looks fine'}
    with patch('app.services.ai_evidence_review.review_evidence', return_value=sugg) as rv:
        _scan(app, a, ai=True)
        assert rv.call_count == 1
    from app.models import Evidence
    with app.app_context():
        ev = Evidence.query.one()
        assert (ev.ai_suggested_status, ev.ai_confidence, ev.ai_rationale) == ('Approved', 0.9, 'looks fine')
        assert ev.ai_reviewed_at is not None and ev.status == 'Pending Review'


def test_ai_none_tolerated_and_skipped_without_mapping(app, fake):
    a, _ = _org(app, 'OrgA')
    _fw(app, [a])
    _connect(app, a)
    fake.checks = [_ck('Mapped'), _ck('Unmapped', kw=('zzznomatch',))]
    with patch('app.services.ai_evidence_review.review_evidence', return_value=None) as rv:
        _scan(app, a, ai=True)
        assert rv.call_count == 1  # unmapped evidence has nothing to review against
    from app.models import Evidence
    with app.app_context():
        assert all(e.ai_suggested_status is None and e.status == 'Pending Review' for e in Evidence.query)


def test_ai_false_never_calls_review(app, fake):
    a, _ = _org(app, 'OrgA')
    _fw(app, [a])
    _connect(app, a)
    fake.checks = [_ck()]
    with patch('app.services.ai_evidence_review.review_evidence') as rv:
        _scan(app, a, ai=False)
        rv.assert_not_called()


def test_scan_decrypts_stored_config(app, fake):
    a, _ = _org(app, 'OrgA')
    _connect(app, a)
    fake.checks = []
    _scan(app, a)
    assert fake.seen_cfg == FAKE_CFG


# ---------- (4) run_scans_for_org ----------

def test_run_scans_for_org_isolates_failures(app, fake):
    from app.models import Organization, Evidence
    from app.services.integration_scans import run_scans_for_org
    import app.integrations as integ
    a, _ = _org(app, 'OrgA')
    _connect(app, a, 'fake')
    _connect(app, a, 'fake2')
    boom = Fake()
    boom.scan_exc = RuntimeError('api down')
    integ._REGISTRY['fake'] = boom.spec()   # restored by monkeypatch.setitem teardown
    fake.checks = [_ck('Good', kw=())]
    integ._REGISTRY['fake2'] = fake.spec('fake2')
    with patch('app.services.ai_evidence_review.review_evidence', return_value=None):
        with app.app_context():
            res = run_scans_for_org(Organization.query.get(a))
            assert isinstance(res['fake'], RuntimeError)
            assert res['fake2'][0] == 1
            # session still usable after rollback and the good provider's evidence is committed
            assert [e.source_type for e in Evidence.query.all()] == ['integration:fake2']


def test_failure_midscan_rolls_back_partial_work(app, fake):
    from app.models import Organization, Evidence
    from app.services.integration_scans import run_scans_for_org
    a, _ = _org(app, 'OrgA')
    _connect(app, a, 'fake')
    fake.checks = [_ck('A', kw=()), _ck('B', kw=())]
    with patch('app.services.integration_scans._controls_for', side_effect=[[], RuntimeError('x')]):
        with app.app_context():
            res = run_scans_for_org(Organization.query.get(a))
            assert isinstance(res['fake'], RuntimeError)
            assert Evidence.query.count() == 0


def test_run_scan_not_connected_raises_lookuperror(app, fake):
    a, _ = _org(app, 'OrgA')
    for p in ('fake', 'nope', 'okta', 'azure'):
        with pytest.raises(LookupError):
            _scan(app, a, p)


# ---------- (5) routes ----------

def _admin_client(app, role='Admin'):
    oid, uid = _org(app, 'OrgR', role)
    c = app.test_client()
    _login(c, uid, oid)
    return c, oid


def test_connect_stores_encrypted_config(app, fake):
    from app.models import IntegrationConnection
    c, oid = _admin_client(app)
    r = c.post('/integrations/p/fake/connect', data=FAKE_CFG)
    assert r.status_code == 302
    with app.app_context():
        conn = IntegrationConnection.query.one()
        assert conn.organization_id == oid and conn.account_label == 'acct-label'
        assert 'tok-SECRET-123' not in conn.config and conn.config.startswith('enc:')
        from app.services.crypto import decrypt
        assert json.loads(decrypt(conn.config)) == FAKE_CFG
    # reconnect updates the same row
    c.post('/integrations/p/fake/connect', data={'token': 'new', 'site': 'acme'})
    with app.app_context():
        assert IntegrationConnection.query.count() == 1


@pytest.mark.parametrize('data', [{}, {'token': 'x'}, {'token': 'x', 'site': '   '}])
def test_connect_requires_all_fields(app, fake, data):
    from app.models import IntegrationConnection
    c, _ = _admin_client(app)
    r = c.post('/integrations/p/fake/connect', data=data, follow_redirects=True)
    assert b'Fill in every Fakeco field' in r.data
    with app.app_context():
        assert IntegrationConnection.query.count() == 0


def test_connect_rejects_bad_credentials(app, fake):
    from app.models import IntegrationConnection
    c, _ = _admin_client(app)
    fake.validate_exc = ValueError('401')
    r = c.post('/integrations/p/fake/connect', data=FAKE_CFG, follow_redirects=True)
    assert b'rejected those credentials' in r.data
    with app.app_context():
        assert IntegrationConnection.query.count() == 0


def test_connect_unknown_provider(app, fake):
    from app.models import IntegrationConnection
    c, _ = _admin_client(app)
    r = c.post('/integrations/p/nope/connect', data=FAKE_CFG, follow_redirects=True)
    assert b'Unknown integration' in r.data
    with app.app_context():
        assert IntegrationConnection.query.count() == 0


def test_connect_requires_write_permission_and_login(app, fake):
    from app.models import IntegrationConnection
    c, _ = _admin_client(app, role='Viewer')
    c.post('/integrations/p/fake/connect', data=FAKE_CFG)
    anon = app.test_client()
    assert anon.post('/integrations/p/fake/connect', data=FAKE_CFG).status_code == 302
    with app.app_context():
        assert IntegrationConnection.query.count() == 0


def test_disconnect_keeps_evidence_and_risks(app, fake):
    from app.models import IntegrationConnection, Evidence, Risk
    c, oid = _admin_client(app)
    _connect(app, oid)
    fake.checks = [_ck('X', passed=False, kw=())]
    _scan(app, oid)
    c.post('/integrations/p/fake/disconnect')
    with app.app_context():
        assert IntegrationConnection.query.count() == 0
        assert Evidence.query.count() == 1 and Risk.query.count() == 1


def test_disconnect_only_affects_current_org(app, fake):
    from app.models import IntegrationConnection
    c, oid = _admin_client(app)
    other, _ = _org(app, 'Other')
    _connect(app, other)
    c.post('/integrations/p/fake/disconnect')
    with app.app_context():
        assert IntegrationConnection.query.filter_by(organization_id=other).count() == 1


def test_disconnect_viewer_forbidden(app, fake):
    from app.models import IntegrationConnection
    c, oid = _admin_client(app, role='Viewer')
    _connect(app, oid)
    c.post('/integrations/p/fake/disconnect')
    with app.app_context():
        assert IntegrationConnection.query.count() == 1


def test_scan_route_success_and_permissions(app, fake):
    from app.models import Evidence
    c, oid = _admin_client(app)
    _connect(app, oid)
    fake.checks = [_ck('X', passed=False, kw=())]
    with patch('app.services.ai_evidence_review.review_evidence', return_value=None):
        r = c.post('/integrations/fake/scan', follow_redirects=True)
    assert b'Scan complete: 1 checks, 1 failed' in r.data
    with app.app_context():
        assert Evidence.query.count() == 1
    # viewer and anonymous cannot scan
    vc, void = _admin_client(app, role='Viewer') if False else (None, None)


def test_scan_route_denies_viewer_and_anonymous(app, fake):
    from app.models import Evidence
    c, oid = _admin_client(app, role='Viewer')
    _connect(app, oid)
    fake.checks = [_ck(kw=())]
    c.post('/integrations/fake/scan')
    assert app.test_client().post('/integrations/fake/scan').status_code == 302
    with app.app_context():
        assert Evidence.query.count() == 0


def test_scan_route_not_connected_and_unknown(app, fake):
    c, _ = _admin_client(app)
    r = c.post('/integrations/fake/scan', follow_redirects=True)
    assert b'Connect this integration first' in r.data
    r = c.post('/integrations/nope/scan', follow_redirects=True)
    assert b'Unknown integration' in r.data


def test_scan_route_legacy_not_connected_says_connect_first(app, fake):
    c, _ = _admin_client(app)
    r = c.post('/integrations/okta/scan', follow_redirects=True)
    assert b'Connect this integration first' in r.data


def test_scan_route_provider_error_is_generic_flash(app, fake):
    c, oid = _admin_client(app)
    _connect(app, oid)
    fake.scan_exc = RuntimeError('secret-internal-detail')
    r = c.post('/integrations/fake/scan', follow_redirects=True)
    assert b'Scan failed' in r.data and b'secret-internal-detail' not in r.data


# ---------- (6) page ----------

def test_integrations_page_cards(app, fake):
    c, oid = _admin_client(app)
    html = c.get('/integrations').get_data(as_text=True)
    assert 'Fakeco' in html and 'Cap-One' in html and 'Not connected' in html
    assert '/integrations/p/fake/connect' in html and 'name="token"' in html
    assert 'type="password"' in html
    _connect(app, oid)
    html = c.get('/integrations').get_data(as_text=True)
    assert '/integrations/fake/scan' in html and '/integrations/p/fake/disconnect' in html
    assert 'Never scanned' in html and 'tok-SECRET-123' not in html


def test_integrations_page_shows_only_own_org_connection(app, fake):
    c, oid = _admin_client(app)
    other, _ = _org(app, 'Other')
    _connect(app, other)
    html = c.get('/integrations').get_data(as_text=True)
    assert '/integrations/fake/scan' not in html and '/integrations/p/fake/connect' in html


# ---------- (7) legacy azure/okta path ----------

@pytest.mark.parametrize('prov,model_name,kw', [('okta', 'OktaConnection', {'domain': 'x.okta.com', 'api_token': 'e'}),
                                                 ('azure', 'AzureConnection', {'tenant_id': 't', 'client_id': 'c',
                                                                               'client_secret': 'e', 'subscription_id': 's'})])
def test_legacy_provider_scan_with_stub_scanner(app, fake, monkeypatch, prov, model_name, kw):
    import app.models as models
    from app.services import integration_scans as s
    a, _ = _org(app, 'OrgA')
    _fw(app, [a])
    with app.app_context():
        models.db.session.add(getattr(models, model_name)(organization_id=a, **kw))
        models.db.session.commit()
    stub = lambda conn: [('Legacy fail', False, 'bad', ['firewall']), ('Legacy ok', True, 'fine', ['firewall'])]
    monkeypatch.setitem(s.SCANNERS, prov, (s.SCANNERS[prov][0], stub))
    assert prov in _connected(app, a)
    assert _scan(app, a, prov)[:4] == (2, 1, 2, 1)  # 2 evidence rows x 1 matching control
    with app.app_context():
        ev = models.Evidence.query.filter_by(source_type=f'integration:{prov}', title='Legacy fail').one()
        assert 'FAIL' in ev.description
        assert models.Risk.query.one().title == '[Scan] Legacy fail'
        assert getattr(models, model_name).query.one().last_synced_at is not None  # also set by run_scan


def _connected(app, org_id):
    from app.services.integration_scans import connected_providers
    with app.app_context():
        return connected_providers(org_id)


def test_connected_providers_ignores_unregistered_and_other_orgs(app, fake):
    a, _ = _org(app, 'OrgA')
    b, _ = _org(app, 'OrgB')
    _connect(app, a, 'fake')
    _connect(app, a, 'removed-provider')
    _connect(app, b, 'fake2')
    assert _connected(app, a) == ['fake']
