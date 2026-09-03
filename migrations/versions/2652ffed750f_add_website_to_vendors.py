"""add website to vendors

Revision ID: 2652ffed750f
Revises: 51d4881f4341
Create Date: 2026-09-03 17:21:06.172837

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2652ffed750f'
down_revision = '51d4881f4341'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('vendors', schema=None) as batch_op:
        batch_op.add_column(sa.Column('website', sa.String(length=300), nullable=True))


def downgrade():
    with op.batch_alter_table('vendors', schema=None) as batch_op:
        batch_op.drop_column('website')
