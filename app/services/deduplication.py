import logging
from sqlalchemy import func

logger = logging.getLogger(__name__)


def cleanup_duplicate_frameworks(session=None):
    """Finds and removes duplicate frameworks in the database.

    For frameworks with the same name and organization_id (or both None for shared library):
    keeps the one with the highest number of controls (and lowest ID as tie-breaker),
    re-points any foreign keys if necessary, and safely removes the redundant duplicate.
    """
    from app.models import db, Framework, Control, ComplianceSnapshot

    if session is None:
        session = db.session

    try:
        # 1. Clean up duplicate shared frameworks (organization_id IS NULL)
        shared_duplicates = (
            session.query(Framework.name)
            .filter(Framework.organization_id.is_(None))
            .group_by(Framework.name)
            .having(func.count(Framework.id) > 1)
            .all()
        )

        for (name,) in shared_duplicates:
            fws = (
                Framework.query
                .filter(Framework.organization_id.is_(None), Framework.name == name)
                .all()
            )
            if len(fws) <= 1:
                continue

            # Sort so the one with most controls is first, then lowest id
            fws.sort(key=lambda f: (f.controls.count(), -f.id), reverse=True)
            winner = fws[0]
            duplicates = fws[1:]

            logger.info(f"Deduplicating shared framework '{name}': keeping ID={winner.id} ({winner.controls.count()} controls), removing duplicates: {[d.id for d in duplicates]}")

            for dup in duplicates:
                # Repoint snapshots
                ComplianceSnapshot.query.filter_by(framework_id=dup.id).update(
                    {'framework_id': winner.id}, synchronize_session=False
                )
                # Safely handle snapshots: delete duplicate snapshots for dates that already exist on winner
                for snap in ComplianceSnapshot.query.filter_by(framework_id=dup.id).all():
                    existing = ComplianceSnapshot.query.filter_by(
                        organization_id=snap.organization_id,
                        framework_id=winner.id,
                        snapshot_date=snap.snapshot_date,
                    ).first()
                    if existing:
                        session.delete(snap)
                    else:
                        snap.framework_id = winner.id

                # Repoint controls if any existed on duplicate
                Control.query.filter_by(framework_id=dup.id).update(
                    {'framework_id': winner.id}, synchronize_session=False
                )
                session.delete(dup)

            session.commit()

        # 2. Clean up duplicate custom frameworks per organization
        org_duplicates = (
            session.query(Framework.organization_id, Framework.name)
            .filter(Framework.organization_id.isnot(None))
            .group_by(Framework.organization_id, Framework.name)
            .having(func.count(Framework.id) > 1)
            .all()
        )

        for org_id, name in org_duplicates:
            fws = (
                Framework.query
                .filter(Framework.organization_id == org_id, Framework.name == name)
                .all()
            )
            if len(fws) <= 1:
                continue

            fws.sort(key=lambda f: (f.controls.count(), -f.id), reverse=True)
            winner = fws[0]
            duplicates = fws[1:]

            logger.info(f"Deduplicating org {org_id} framework '{name}': keeping ID={winner.id}, removing duplicates: {[d.id for d in duplicates]}")

            for dup in duplicates:
                ComplianceSnapshot.query.filter_by(framework_id=dup.id).update(
                    {'framework_id': winner.id}, synchronize_session=False
                )
                for snap in ComplianceSnapshot.query.filter_by(framework_id=dup.id).all():
                    existing = ComplianceSnapshot.query.filter_by(
                        organization_id=snap.organization_id,
                        framework_id=winner.id,
                        snapshot_date=snap.snapshot_date,
                    ).first()
                    if existing:
                        session.delete(snap)
                    else:
                        snap.framework_id = winner.id

                Control.query.filter_by(framework_id=dup.id).update(
                    {'framework_id': winner.id}, synchronize_session=False
                )
                session.delete(dup)

            session.commit()

    except Exception as e:
        session.rollback()
        logger.warning(f"Framework deduplication encountered an error (rolled back): {e}")

