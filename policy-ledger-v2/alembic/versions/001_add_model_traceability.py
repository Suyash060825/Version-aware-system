"""Add model_name and model_version columns to chat_message and indexing_job

Revision ID: 001_add_model_traceability
Revises: 
Create Date: 2026-08-10 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_model_traceability'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Upgrade ChatMessage
    with op.batch_alter_table('chat_message', schema=None) as batch_op:
        batch_op.add_column(sa.Column('model_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('model_version', sa.String(length=50), nullable=True))

    # Upgrade IndexingJob
    with op.batch_alter_table('indexing_job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('model_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('model_version', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('indexing_job', schema=None) as batch_op:
        batch_op.drop_column('model_version')
        batch_op.drop_column('model_name')

    with op.batch_alter_table('chat_message', schema=None) as batch_op:
        batch_op.drop_column('model_version')
        batch_op.drop_column('model_name')
