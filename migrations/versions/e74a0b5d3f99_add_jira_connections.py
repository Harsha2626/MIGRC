"""add jira_connections and risks.jira_key

Revision ID: e74a0b5d3f99
Revises: d63f9a4c2e88
Create Date: 2026-11-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'e74a0b5d3f99'
down_revision = 'd63f9a4c2e88'
branch_labels = None
depends_on = None


def upgrade():
    # create_app() runs db.create_all() at boot, so the table may already exist (create_all never adds columns, though).
    insp = sa.inspect(op.get_bind())
    if 'jira_connections' not in insp.get_table_names():
        op.create_table(
            'jira_connections',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False, unique=True),
            sa.Column('site_url', sa.String(255), nullable=False),
            sa.Column('email', sa.String(255), nullable=False),
            sa.Column('api_token', sa.Text(), nullable=False),
            sa.Column('project_key', sa.String(20), nullable=False),
            sa.Column('connected_by_id', sa.Integer(), sa.ForeignKey('users.id')),
            sa.Column('connected_at', sa.DateTime()),
        )
    if 'jira_key' not in [c['name'] for c in insp.get_columns('risks')]:
        with op.batch_alter_table('risks') as b:
            b.add_column(sa.Column('jira_key', sa.String(30)))


def downgrade():
    with op.batch_alter_table('risks') as b:
        b.drop_column('jira_key')
    op.drop_table('jira_connections')
