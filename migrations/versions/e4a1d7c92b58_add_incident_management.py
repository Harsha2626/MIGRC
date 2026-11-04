"""add incident management tables

Revision ID: e4a1d7c92b58
Revises: b3c8e1d27a45
Create Date: 2026-11-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'e4a1d7c92b58'
down_revision = 'b3c8e1d27a45'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'incidents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=True),
        sa.Column('reported_by_id', sa.Integer(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('affected_assets', sa.Text(), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('resolution_summary', sa.Text(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('lessons_learned', sa.Text(), nullable=True),
        sa.Column('follow_up_actions', sa.Text(), nullable=True),
        sa.Column('review_completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['reported_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_incidents_organization_id', 'incidents', ['organization_id'])

    op.create_table(
        'incident_timeline_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('incident_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=True),
        sa.Column('entry_type', sa.String(length=20), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id']),
        sa.ForeignKeyConstraint(['author_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_incident_timeline_entries_incident_id', 'incident_timeline_entries', ['incident_id'])

    op.create_table(
        'incident_controls',
        sa.Column('incident_id', sa.Integer(), nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id']),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id']),
        sa.PrimaryKeyConstraint('incident_id', 'control_id'),
    )
    op.create_table(
        'incident_risks',
        sa.Column('incident_id', sa.Integer(), nullable=False),
        sa.Column('risk_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id']),
        sa.ForeignKeyConstraint(['risk_id'], ['risks.id']),
        sa.PrimaryKeyConstraint('incident_id', 'risk_id'),
    )


def downgrade():
    op.drop_table('incident_risks')
    op.drop_table('incident_controls')
    op.drop_index('ix_incident_timeline_entries_incident_id', table_name='incident_timeline_entries')
    op.drop_table('incident_timeline_entries')
    op.drop_index('ix_incidents_organization_id', table_name='incidents')
    op.drop_table('incidents')
