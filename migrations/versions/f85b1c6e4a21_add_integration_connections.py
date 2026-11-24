"""add integration_connections (generic provider credentials)

Revision ID: f85b1c6e4a21
Revises: e74a0b5d3f99
"""
from alembic import op
import sqlalchemy as sa

revision = 'f85b1c6e4a21'
down_revision = 'e74a0b5d3f99'
branch_labels = None
depends_on = None


def upgrade():
    if 'integration_connections' not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            'integration_connections',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False),
            sa.Column('provider', sa.String(40), nullable=False),
            sa.Column('config', sa.Text(), nullable=False),
            sa.Column('account_label', sa.String(255)),
            sa.Column('connected_by_id', sa.Integer(), sa.ForeignKey('users.id')),
            sa.Column('connected_at', sa.DateTime()),
            sa.Column('last_synced_at', sa.DateTime()),
            sa.UniqueConstraint('organization_id', 'provider'))


def downgrade():
    op.drop_table('integration_connections')
