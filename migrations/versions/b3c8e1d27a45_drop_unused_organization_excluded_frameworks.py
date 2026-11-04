"""drop unused organization_excluded_frameworks table (model removed; opt-in
organization_frameworks replaced the exclusion approach)

Revision ID: b3c8e1d27a45
Revises: f79ad4185315
Create Date: 2026-11-04 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b3c8e1d27a45'
down_revision = 'f79ad4185315'
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent and conservative: only drop if present AND empty (no data is ever lost).
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if 'organization_excluded_frameworks' not in insp.get_table_names():
        return
    count = conn.execute(sa.text('SELECT COUNT(*) FROM organization_excluded_frameworks')).scalar()
    if count == 0:
        op.drop_table('organization_excluded_frameworks')


def downgrade():
    # The table was unused; recreating it is unnecessary.
    pass
