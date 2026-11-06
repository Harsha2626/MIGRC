"""Add scope_reason to control_statuses

Revision ID: a7c3e91f5d20
Revises: e4a1d7c92b58
"""
from alembic import op
import sqlalchemy as sa

revision = 'a7c3e91f5d20'
down_revision = 'e4a1d7c92b58'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('control_statuses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('scope_reason', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('control_statuses', schema=None) as batch_op:
        batch_op.drop_column('scope_reason')
