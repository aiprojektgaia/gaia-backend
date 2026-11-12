"""Add default interfaces

Revision ID: e0a9b5baf59e
Revises: 74b192026e9c
Create Date: 2024-11-12 12:00:19.883702

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e0a9b5baf59e"
down_revision: Union[str, None] = "74b192026e9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("INSERT INTO interface_group (name) VALUES ('Vectorization')")
    op.execute("insert into interface_group (name) values ('Internal')")


def downgrade() -> None:
    op.execute("""
               DELETE FROM interface_group WHERE name = 'Vectorization';
               DELETE FROM interface_group WHERE name = 'Internal';
               """)
