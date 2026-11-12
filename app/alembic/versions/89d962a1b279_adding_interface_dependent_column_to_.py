"""Adding interface dependent column to TaskType

Revision ID: 89d962a1b279
Revises: c5b6096014ba
Create Date: 2025-01-15 10:19:34.846495

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89d962a1b279'
down_revision: Union[str, None] = 'c5b6096014ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "task_type", sa.Column("is_interface_dependent", sa.BOOLEAN(), nullable=True, default=True)
    )

    op.execute("""
        UPDATE task_type
        SET is_interface_dependent = true
        ;
    """)

    op.execute("""
        UPDATE task_type
        SET is_interface_dependent = false
        WHERE name = 'TileImagesSrc' OR name = 'TileImagesBase' 
        ;
    """)

    op.alter_column("task_type", "is_interface_dependent", nullable=False)


def downgrade() -> None:
    op.drop_column("task_type", "is_interface_dependent")
