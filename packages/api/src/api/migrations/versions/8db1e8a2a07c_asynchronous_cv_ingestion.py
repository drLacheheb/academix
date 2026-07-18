"""asynchronous cv ingestion columns and nullable candidate profiles

Revision ID: 8db1e8a2a07c
Revises: 0e9403cb1b73
Create Date: 2026-07-18 13:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8db1e8a2a07c'
down_revision: Union[str, None] = '0e9403cb1b73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('candidate_profiles', schema=None) as batch_op:
        batch_op.alter_column('name', existing_type=sa.String(), nullable=True)
        batch_op.alter_column('email', existing_type=sa.String(), nullable=True)
        batch_op.add_column(sa.Column('status', sa.String(), nullable=False, server_default='INGESTING'))
        batch_op.add_column(sa.Column('status_message', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('claimed_by', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('claimed_at', sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f('ix_candidate_profiles_status'), ['status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('candidate_profiles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_candidate_profiles_status'))
        batch_op.drop_column('claimed_at')
        batch_op.drop_column('claimed_by')
        batch_op.drop_column('status_message')
        batch_op.drop_column('status')
        batch_op.alter_column('email', existing_type=sa.String(), nullable=False)
        batch_op.alter_column('name', existing_type=sa.String(), nullable=False)
