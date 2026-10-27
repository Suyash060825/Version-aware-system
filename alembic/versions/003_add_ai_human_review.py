"""Add AI human review states
Revision ID: 003_add_ai_human_review
Revises: 002_add_chat_tokens
Create Date: 2026-08-12 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '003_add_ai_human_review'
down_revision = '002_add_chat_tokens'
branch_labels = None
depends_on = None

def upgrade():
    # MeetingMinutes
    with op.batch_alter_table('meeting_minutes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('review_status', sa.String(length=30), nullable=True, server_default='ai_generated'))
        batch_op.add_column(sa.Column('reviewed_by_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True))
        batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(), nullable=True))

    # PolicyAIInsight
    with op.batch_alter_table('policy_ai_insight', schema=None) as batch_op:
        batch_op.add_column(sa.Column('review_status', sa.String(length=30), nullable=True, server_default='ai_generated'))
        batch_op.add_column(sa.Column('reviewed_by_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True))
        batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(), nullable=True))

def downgrade():
    with op.batch_alter_table('policy_ai_insight', schema=None) as batch_op:
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('reviewed_by_id')
        batch_op.drop_column('review_status')

    with op.batch_alter_table('meeting_minutes', schema=None) as batch_op:
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('reviewed_by_id')
        batch_op.drop_column('review_status')
