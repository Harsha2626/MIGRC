"""remove vendor risk tier and risk score

Revision ID: 51d4881f4341
Revises: 7a2e9c4f1b3d
Create Date: 2026-09-03 17:09:22.082032

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '51d4881f4341'
down_revision = '7a2e9c4f1b3d'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('vendor_risk_snapshots')
    with op.batch_alter_table('vendors', schema=None) as batch_op:
        batch_op.drop_column('risk_tier')
        batch_op.drop_column('risk_score')


def downgrade():
    with op.batch_alter_table('vendors', schema=None) as batch_op:
        batch_op.add_column(sa.Column('risk_score', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('risk_tier', sa.VARCHAR(length=20), autoincrement=False, nullable=True))

    op.create_table('vendor_risk_snapshots',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('vendor_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('risk_score', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('snapshot_date', sa.DATE(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], name=op.f('vendor_risk_snapshots_vendor_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('vendor_risk_snapshots_pkey'))
    )
