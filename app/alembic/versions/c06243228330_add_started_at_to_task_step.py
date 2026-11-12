"""Add started_at to task_step

Revision ID: c06243228330
Revises: 13eede676796
Create Date: 2025-02-04 11:02:36.324482

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c06243228330"
down_revision: Union[str, None] = "13eede676796"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "task_step", sa.Column("started_at", sa.TIMESTAMP(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("task_step", "started_at")
