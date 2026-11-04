"""
Additively load the shared compliance framework library (Framework + Control rows,
organization_id=None, visible to every org) from scripts/data/compliance_frameworks.json.

Non-destructive: does NOT drop or modify existing data. Skips any framework whose
name already exists in the shared library (e.g. ISO 27001:2022, SOC 2 from app/seed.py).

Run: python -m scripts.seed_frameworks
"""
import json
from pathlib import Path

from app import create_app
from app.models import db, Framework, Control

DATA_FILE = Path(__file__).parent / "data" / "compliance_frameworks.json"


def seed_frameworks_in_context():
    """Additively seed the shared library inside an active app context.
    Returns (added, skipped, total). Safe to re-run."""
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    existing_names = {
        name for (name,) in db.session.query(Framework.name)
        .filter(Framework.organization_id.is_(None))
    }

    added, skipped = 0, 0
    for fw in data:
        name = fw["name"].strip()
        if name in existing_names:
            skipped += 1
            continue

        controls = fw.get("controls", [])
        framework = Framework(
            name=name,
            description=fw.get("description", ""),
            category=fw.get("category", ""),
            icon=fw.get("icon", "globe"),
            status="Not Started",
            controls_detail=f"{len(controls)} controls",
        )
        db.session.add(framework)
        db.session.flush()  # assign framework.id

        for c in controls:
            db.session.add(Control(
                code=c.get("code", ""),
                title=c.get("title", ""),
                description=c.get("description", ""),
                category=c.get("category", ""),
                framework_id=framework.id,
                test_criteria=c.get("test_criteria", ""),
                evidence_requirement=c.get("evidence_requirement", ""),
            ))
        added += 1

    db.session.commit()
    total = Framework.query.filter(Framework.organization_id.is_(None)).count()
    return added, skipped, total


def seed_frameworks():
    app = create_app()
    with app.app_context():
        added, skipped, total = seed_frameworks_in_context()
        print(f"Added {added} frameworks, skipped {skipped} (name already present).")
        print(f"Shared framework library now has {total} frameworks.")


if __name__ == "__main__":
    seed_frameworks()
