"""One-off: copy every table from a Postgres DB into a fresh local sqlite file (schema from app models).
Usage: python scripts/migrate_pg_to_sqlite.py <source_url> <dest_sqlite_path>"""
import os, sys
src_url, dest = sys.argv[1], os.path.abspath(sys.argv[2])
if os.path.exists(dest):
    sys.exit(f'{dest} already exists; refusing to overwrite')
os.environ['DATABASE_URL'] = 'sqlite:///' + dest  # create_app builds the schema here
from sqlalchemy import create_engine, MetaData, text
from app import create_app
from app.models import db

app = create_app()
with app.app_context():
    db.create_all()
    src = create_engine(src_url)
    smeta = MetaData(); smeta.reflect(bind=src)
    missing = set(smeta.tables) - set(db.metadata.tables)
    if missing:
        print('WARNING: source tables not in models (skipped):', sorted(missing))
    with src.connect() as s, db.engine.begin() as d:
        d.execute(text('PRAGMA foreign_keys=OFF'))
        for t in db.metadata.sorted_tables:
            if t.name not in smeta.tables:
                print(f'{t.name}: not in source'); continue
            cols = [c.name for c in t.columns if c.name in smeta.tables[t.name].columns]
            rows = [dict(r._mapping) for r in s.execute(smeta.tables[t.name].select())]
            rows = [{k: r[k] for k in cols} for r in rows]
            if rows:
                d.execute(t.insert(), rows)
            print(f'{t.name}: {len(rows)}')
