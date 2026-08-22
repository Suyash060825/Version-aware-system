"""Add token usage and cache_hit columns to chat_message

Revision ID: 002_add_chat_tokens
Revises: 001_add_model_traceability
Create Date: 2026-08-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_chat_tokens'
down_revision = '001_add_model_traceability'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('chat_message', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prompt_tokens', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('completion_tokens', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('model_used', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('cache_hit', sa.Boolean(), nullable=True, server_default='0'))


def downgrade():
    with op.batch_alter_table('chat_message', schema=None) as batch_op:
        batch_op.drop_column('cache_hit')
        batch_op.drop_column('model_used')
        batch_op.drop_column('completion_tokens')
        batch_op.drop_column('prompt_tokens')
