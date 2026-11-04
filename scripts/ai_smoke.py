"""Live smoke test for MIGRC's AI path (NOT run in CI).

Exercises the real local OpenCode server: status, model discovery, a trivial dispatch, and the
vendor-questionnaire suggester against a throwaway sqlite DB seeded with one org. Never touches
the configured database and never prints secrets.

Usage (from repo root):
    python scripts/ai_smoke.py [--env /path/to/.env]

Reads OPENCODE_SERVER_PASSWORD (and optional OPENCODE_SERVER_URL) from the environment, or from
the --env file. Unsets OPENCODE_MODEL so the OpenCode-server primary path is what gets tested.
"""
import argparse
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', help='optional .env file to load OPENCODE_* variables from')
    ap.add_argument('--pinned', action='store_true',
                    help='keep OPENCODE_MODEL/CLINE_API_KEY from --env (tests the opt-in pinned path)')
    args = ap.parse_args()
    if args.env:
        from dotenv import dotenv_values
        for k, v in dotenv_values(args.env).items():
            if k.startswith('OPENCODE_') and k not in os.environ:
                os.environ[k] = v
    import logging
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(name)s: %(message)s')
    if args.pinned:
        # exercise the opt-in pinned path (e.g. clinedirect/...) using the env file's settings
        from dotenv import dotenv_values
        for k, v in dotenv_values(args.env).items():
            if k in ('OPENCODE_MODEL', 'OPENCODE_MODEL_VARIANT', 'CLINE_API_KEY'):
                os.environ.setdefault(k, v)
    else:
        os.environ.pop('OPENCODE_MODEL', None)
        os.environ.pop('OPENCODE_MODEL_VARIANT', None)
    if not os.environ.get('OPENCODE_SERVER_PASSWORD'):
        print('FAIL: OPENCODE_SERVER_PASSWORD not set')
        return 2

    fd, db_path = tempfile.mkstemp(suffix='.db', prefix='ai_smoke_')
    os.close(fd)
    os.environ['DATABASE_URL'] = 'sqlite:///' + db_path
    os.environ['FLASK_ENV'] = 'development'

    from app import create_app
    from app.models import (db, Organization, Policy, Evidence, QuestionnaireTemplate,
                            QuestionnaireQuestion, Vendor, VendorAssessment)
    from app.services import ai_dispatch, ai_questionnaire

    used_models = []
    real_request = ai_dispatch._request

    def spy(base_url, password, method, path, body=None, timeout=ai_dispatch.REQUEST_TIMEOUT):
        if method == 'POST' and path.endswith('/prompt'):
            used_models.append(body['model']['modelID'])
        return real_request(base_url, password, method, path, body, timeout)

    ai_dispatch._request = spy
    ok = True
    app = create_app()
    try:
        with app.app_context():
            db.create_all()
            print('status:', ai_dispatch.get_ai_status())

            t0 = time.monotonic()
            reply = ai_dispatch.run_compliance_agent(
                'Reply with ONLY a ```json block: {"ok": true}',
                lambda t: ('ok' in t) and t, log_tag='smoke')
            dt = time.monotonic() - t0
            print(f'dispatch: {"OK" if reply else "FAIL"} in {dt:.1f}s models tried: {used_models}')
            ok &= bool(reply)

            org = Organization(name='Smoke Org', slug='smoke-org')
            db.session.add(org)
            db.session.flush()
            db.session.add_all([
                Policy(organization_id=org.id, name='Access Control Policy', status='Published',
                       content='All production access requires MFA and quarterly access reviews.'),
                Evidence(organization_id=org.id, title='Q3 access review log', status='Approved',
                         description='Quarterly review of production access, signed by CISO.'),
            ])
            tpl = QuestionnaireTemplate(organization_id=org.id, name='Smoke')
            db.session.add(tpl)
            db.session.flush()
            db.session.add_all([
                QuestionnaireQuestion(template_id=tpl.id, question_text='Do you require MFA for production access?'),
                QuestionnaireQuestion(template_id=tpl.id, question_text='Are you ISO 27001 certified?'),
            ])
            vendor = Vendor(organization_id=org.id, name='Acme')
            db.session.add(vendor)
            db.session.flush()
            asm = VendorAssessment(vendor_id=vendor.id, template_id=tpl.id)
            db.session.add(asm)
            db.session.commit()

            used_models.clear()
            t0 = time.monotonic()
            result = ai_questionnaire.suggest_answers(asm, org.id)
            dt = time.monotonic() - t0
            print(f'questionnaire: {"OK" if result else "FAIL"} in {dt:.1f}s models tried: {used_models}')
            for qid, s in (result or {}).items():
                print(f'  Q{qid}: conf={s["confidence"]:.2f} cites={s["cites"]} needs_human={s["needs_human"]}')
                print(f'    {s["answer"][:160]!r}')
            ok &= bool(result)
            db.engine.dispose()
    finally:
        os.remove(db_path)
    print('RESULT:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
