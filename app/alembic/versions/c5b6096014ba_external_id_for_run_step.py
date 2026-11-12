"""external id for run_step

Revision ID: c5b6096014ba
Revises: e0a9b5baf59e
Create Date: 2024-11-12 15:03:11.818873

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c5b6096014ba"
down_revision: Union[str, None] = "e0a9b5baf59e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "task_step", sa.Column("external_id", sa.UUID(), nullable=False)
    )

    op.add_column(
        "task_step", sa.Column("status", sa.VARCHAR(), nullable=False)
    )
    pass


def downgrade() -> None:
    op.drop_column("task_step", "external_id")
    op.drop_column("task_step", "status")
