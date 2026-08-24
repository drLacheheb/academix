from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("job_orchestrations", schema=None) as batch_op:
        try:
            batch_op.drop_index(batch_op.f("ix_job_orchestrations_detection_status"))
        except Exception:
            pass
        batch_op.drop_column("detection_claimed_at")
        batch_op.drop_column("detection_claimed_by")
        batch_op.drop_column("detection_status")

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_column("language_code")

    with op.batch_alter_table("candidate_profiles", schema=None) as batch_op:
        batch_op.drop_column("language_code")


def downgrade() -> None:
    with op.batch_alter_table("candidate_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("language_code", sa.String(), nullable=True))

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("language_code", sa.String(), nullable=True))

    with op.batch_alter_table("job_orchestrations", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("detection_status", sa.String(), nullable=False, server_default="PENDING")
        )
        batch_op.add_column(sa.Column("detection_claimed_by", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("detection_claimed_at", sa.DateTime(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_job_orchestrations_detection_status"),
            ["detection_status"],
            unique=False,
        )
