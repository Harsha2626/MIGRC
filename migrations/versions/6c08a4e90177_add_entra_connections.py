"""add entra_connections

Revision ID: 6c08a4e90177
Revises: a7c3e91f5d20
Create Date: 2026-11-12 11:55:37.376220

"""
from alembic import op
import sqlalchemy as sa

revision = '6c08a4e90177'
down_revision = 'a7c3e91f5d20'
branch_labels = None
depends_on = None


def upgrade():
    # create_app() runs db.create_all() at boot, so the table may already exist.
    if 'entra_connections' in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        'entra_connections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False, unique=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, unique=True),
        sa.Column('account', sa.String(255), nullable=False),
        sa.Column('domain', sa.String(255)),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text()),
        sa.Column('token_expiry', sa.DateTime()),
        sa.Column('connected_by_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('connected_at', sa.DateTime()),
        sa.Column('last_synced_at', sa.DateTime()),
    )


def downgrade():
    op.drop_table('entra_connections')
