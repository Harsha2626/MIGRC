"""Add department to risk_treatments

Revision ID: 7a2e9c4f1b3d
Revises: f154dfc324bd
Create Date: 2026-08-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a2e9c4f1b3d'
down_revision = 'f154dfc324bd'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('risk_treatments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('department', sa.String(length=100), nullable=True))


def downgrade():
    with op.batch_alter_table('risk_treatments', schema=None) as batch_op:
        batch_op.drop_column('department')
