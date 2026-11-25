"""add evidence.ai_gaps (per-gap AI findings with done/ignored state, JSON text)

Revision ID: a1b2c3d4e5f6
Revises: f85b1c6e4a21
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'f85b1c6e4a21'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('evidence') as b:
        b.add_column(sa.Column('ai_gaps', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('evidence') as b:
        b.drop_column('ai_gaps')
