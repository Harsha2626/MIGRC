"""add azure_connections

Revision ID: b41d7e2c9a10
Revises: 6c08a4e90177
Create Date: 2026-11-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'b41d7e2c9a10'
down_revision = '6c08a4e90177'
branch_labels = None
depends_on = None


def upgrade():
    # create_app() runs db.create_all() at boot, so the table may already exist.
    if 'azure_connections' in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        'azure_connections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False, unique=True),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('client_id', sa.String(64), nullable=False),
        sa.Column('client_secret', sa.Text(), nullable=False),
        sa.Column('subscription_id', sa.String(64), nullable=False),
        sa.Column('subscription_name', sa.String(255)),
        sa.Column('connected_by_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('connected_at', sa.DateTime()),
        sa.Column('last_synced_at', sa.DateTime()),
    )


def downgrade():
    op.drop_table('azure_connections')
