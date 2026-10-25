"""Add User clearance and SearchHistory indexes

Revision ID: 004_add_user_clearance_and_search_indexes
Revises: 003_add_ai_human_review
Create Date: 2026-10-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '004_add_user_clearance_and_search_indexes'
down_revision = '003_add_ai_human_review'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clearance', sa.String(length=30), nullable=True, server_default='internal'))

    with op.batch_alter_table('search_history', schema=None) as batch_op:
        batch_op.create_index('ix_search_history_query_text', ['query_text'], unique=False)
        batch_op.create_index('ix_searchhistory_answered_date', ['answered', 'created_at'], unique=False)

def downgrade():
    with op.batch_alter_table('search_history', schema=None) as batch_op:
        batch_op.drop_index('ix_searchhistory_answered_date')
        batch_op.drop_index('ix_search_history_query_text')

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('clearance')
