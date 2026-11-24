"""add slack_connections

Revision ID: d63f9a4c2e88
Revises: c52e8f3b1d77
Create Date: 2026-11-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'd63f9a4c2e88'
down_revision = 'c52e8f3b1d77'
branch_labels = None
depends_on = None


def upgrade():
    # create_app() runs db.create_all() at boot, so the table may already exist.
    if 'slack_connections' in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        'slack_connections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False, unique=True),
        sa.Column('team_id', sa.String(32)),
        sa.Column('team_name', sa.String(255)),
        sa.Column('bot_token', sa.Text(), nullable=False),
        sa.Column('channel', sa.String(100), nullable=False),
        sa.Column('connected_by_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('connected_at', sa.DateTime()),
        sa.Column('last_synced_at', sa.DateTime()),
    )


def downgrade():
    op.drop_table('slack_connections')
