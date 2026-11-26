"""Upload generated evidence (manifest.json) into an org through the real upload route.
Usage: python scripts/upload_iso_evidence.py <dir> <org_id> <user_id> <framework_id>
Runs the app in-process against DATABASE_URL (CSRF off for this process only); the route's own
validation, mapping, AI review and snapshot logic all execute."""
import json, os, sys, mimetypes
d, org, uid, fw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
from app import create_app
from app.models import Control
app = create_app()
app.config.update(WTF_CSRF_ENABLED=False)
c = app.test_client()
with c.session_transaction() as s:
    s['_user_id'], s['_fresh'], s['current_org_id'] = str(uid), True, org
with app.app_context():
    ids = {x.code: x.id for x in Control.query.filter_by(framework_id=fw)}
for m in json.load(open(os.path.join(d, 'manifest.json'))):
    with open(os.path.join(d, m['file']), 'rb') as f:
        r = c.post(f"/compliance/{fw}/control/{ids[m['code']]}/upload", data=dict(
            title=m['title'], description=m['desc'], source_type=m['source'],
            audit_period_start='2026-01-01', audit_period_end='2026-11-20', file=(f, m['file'])),
            content_type='multipart/form-data')
    print(m['code'], r.status_code, m['file'], 'expect', m['expect'], flush=True)
