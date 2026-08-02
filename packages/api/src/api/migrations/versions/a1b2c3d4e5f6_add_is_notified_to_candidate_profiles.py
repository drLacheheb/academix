"""add_is_notified_to_candidate_profiles

Revision ID: a1b2c3d4e5f6
Revises: f50087972584
Create Date: 2026-08-02 08:11:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f50087972584"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("candidate_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_notified", sa.Boolean(), nullable=False, server_default=sa.text("false"))
        )


def downgrade() -> None:
    with op.batch_alter_table("candidate_profiles", schema=None) as batch_op:
        batch_op.drop_column("is_notified")
