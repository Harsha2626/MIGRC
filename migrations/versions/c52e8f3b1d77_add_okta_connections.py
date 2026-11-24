"""add okta_connections

Revision ID: c52e8f3b1d77
Revises: b41d7e2c9a10
Create Date: 2026-11-16 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'c52e8f3b1d77'
down_revision = 'b41d7e2c9a10'
branch_labels = None
depends_on = None


def upgrade():
    # create_app() runs db.create_all() at boot, so the table may already exist.
    if 'okta_connections' in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        'okta_connections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False, unique=True),
        sa.Column('domain', sa.String(255), nullable=False),
        sa.Column('api_token', sa.Text(), nullable=False),
        sa.Column('connected_by_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('connected_at', sa.DateTime()),
        sa.Column('last_synced_at', sa.DateTime()),
    )


def downgrade():
    op.drop_table('okta_connections')
