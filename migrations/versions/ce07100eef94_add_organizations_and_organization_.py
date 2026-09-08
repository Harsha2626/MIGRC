"""add organizations and organization_memberships

Revision ID: ce07100eef94
Revises: ed2b6eea0406
Create Date: 2026-09-07 15:18:59.324721

"""
from datetime import datetime
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select


# revision identifiers, used by Alembic.
revision = 'ce07100eef94'
down_revision = 'ed2b6eea0406'
branch_labels = None
depends_on = None

DEFAULT_ORG_NAME = 'Midevops Services Pvt Ltd'
DEFAULT_ORG_SLUG = 'midevops'


def upgrade():
    op.create_table('organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_table('organization_memberships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'organization_id', name='uq_user_org')
    )

    # Backfill: put every existing user into one default org, carrying their
    # current global role over as that org's membership role 1:1 (zero behavior change).
    connection = op.get_bind()
    now = datetime.utcnow()

    organizations = table('organizations',
        column('id', sa.Integer), column('name', sa.String),
        column('slug', sa.String), column('created_at', sa.DateTime))
    memberships = table('organization_memberships',
        column('user_id', sa.Integer), column('organization_id', sa.Integer),
        column('role', sa.String), column('created_at', sa.DateTime))
    users = table('users', column('id', sa.Integer), column('role', sa.String))

    org_id = connection.execute(
        organizations.insert().values(name=DEFAULT_ORG_NAME, slug=DEFAULT_ORG_SLUG, created_at=now)
        .returning(organizations.c.id)
    ).scalar()

    existing_users = connection.execute(select(users.c.id, users.c.role)).fetchall()
    for user_id, role in existing_users:
        connection.execute(memberships.insert().values(
            user_id=user_id, organization_id=org_id, role=role or 'Viewer', created_at=now))


def downgrade():
    op.drop_table('organization_memberships')
    op.drop_table('organizations')
