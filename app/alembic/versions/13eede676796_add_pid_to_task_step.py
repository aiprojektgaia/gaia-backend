"""Add pid to task_step

Revision ID: 13eede676796
Revises: 89d962a1b279
Create Date: 2025-01-22 16:08:42.030084

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "13eede676796"
down_revision: Union[str, None] = "89d962a1b279"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "task_step",
        sa.Column("pid", sa.Integer(), nullable=True, server_default=None),
    )


def downgrade() -> None:
    op.drop_column("task_step", "pid")
