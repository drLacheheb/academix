"""add_embedding_status_to_orchestrations

Revision ID: 9a8f7e6d5c4b
Revises: 8de6e55899ef, 0e9403cb1b73
Create Date: 2026-07-31 20:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a8f7e6d5c4b"
down_revision: tuple[str, str] = ("8de6e55899ef", "0e9403cb1b73")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("job_orchestrations", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "embedding_status",
                sa.String(),
                nullable=False,
                server_default="PENDING",
            )
        )
        batch_op.add_column(sa.Column("embedding_claimed_by", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("embedding_claimed_at", sa.DateTime(), nullable=True))
        batch_op.create_index(
            "ix_job_orchestrations_embedding_status",
            ["embedding_status"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("job_orchestrations", schema=None) as batch_op:
        batch_op.drop_index("ix_job_orchestrations_embedding_status")
        batch_op.drop_column("embedding_claimed_at")
        batch_op.drop_column("embedding_claimed_by")
        batch_op.drop_column("embedding_status")
