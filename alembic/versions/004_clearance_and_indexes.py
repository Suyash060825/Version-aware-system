"""Add User clearance, policy version fields, chunk v2 fields, and SearchHistory indexes

Revision ID: 004_clearance_and_indexes
Revises: 003_add_ai_human_review
Create Date: 2026-10-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '004_clearance_and_indexes'
down_revision = '003_add_ai_human_review'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clearance', sa.String(length=30), nullable=True, server_default='internal'))

    with op.batch_alter_table('policy_version', schema=None) as batch_op:
        batch_op.add_column(sa.Column('expiration_date', sa.Date(), nullable=True))

    with op.batch_alter_table('policy_chunk_v2', schema=None) as batch_op:
        batch_op.add_column(sa.Column('valid_from_ts', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('valid_to_ts', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')))
        batch_op.add_column(sa.Column('tenant_id', sa.String(length=50), nullable=True, server_default='default'))

    with op.batch_alter_table('search_history', schema=None) as batch_op:
        batch_op.create_index('ix_search_history_query_text', ['query_text'], unique=False)
        batch_op.create_index('ix_searchhistory_answered_date', ['answered', 'created_at'], unique=False)

def downgrade():
    with op.batch_alter_table('search_history', schema=None) as batch_op:
        batch_op.drop_index('ix_searchhistory_answered_date')
        batch_op.drop_index('ix_search_history_query_text')

    with op.batch_alter_table('policy_chunk_v2', schema=None) as batch_op:
        batch_op.drop_column('tenant_id')
        batch_op.drop_column('is_active')
        batch_op.drop_column('valid_to_ts')
        batch_op.drop_column('valid_from_ts')

    with op.batch_alter_table('policy_version', schema=None) as batch_op:
        batch_op.drop_column('expiration_date')

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('clearance')
