"""add organization_frameworks table (opt-in framework adoption) and backfill from existing
engagement, so the shared framework library becomes a catalog orgs explicitly add from instead
of all appearing automatically

Revision ID: f79ad4185315
Revises: 6afe74e30f5c
Create Date: 2026-10-31 16:20:00.000000

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f79ad4185315'
down_revision = '6afe74e30f5c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'organization_frameworks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('framework_id', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['framework_id'], ['frameworks.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'framework_id', name='uq_org_added_fw'),
    )

    # Backfill: preserve today's effective visibility for every org by opting them into any
    # shared framework they already have real engagement with (an assessed control, or a
    # compliance snapshot). Brand-new frameworks just added to the shared library have no such
    # engagement yet, so they correctly start out NOT adopted by anyone - exactly the point of
    # this change: only explicitly-added frameworks should show up in Compliance going forward.
    conn = op.get_bind()

    pairs = set()
    for org_id, framework_id in conn.execute(sa.text("""
        SELECT DISTINCT cs.organization_id, c.framework_id
        FROM control_statuses cs
        JOIN controls c ON c.id = cs.control_id
        JOIN frameworks f ON f.id = c.framework_id
        WHERE f.organization_id IS NULL
    """)):
        pairs.add((org_id, framework_id))

    for org_id, framework_id in conn.execute(sa.text("""
        SELECT DISTINCT snap.organization_id, snap.framework_id
        FROM compliance_snapshots snap
        JOIN frameworks f ON f.id = snap.framework_id
        WHERE f.organization_id IS NULL
    """)):
        pairs.add((org_id, framework_id))

    if pairs:
        org_frameworks_table = sa.table(
            'organization_frameworks',
            sa.column('organization_id', sa.Integer),
            sa.column('framework_id', sa.Integer),
            sa.column('added_at', sa.DateTime),
        )
        now = datetime.utcnow()
        conn.execute(
            org_frameworks_table.insert(),
            [{'organization_id': o, 'framework_id': f, 'added_at': now} for o, f in pairs],
        )


def downgrade():
    op.drop_table('organization_frameworks')
