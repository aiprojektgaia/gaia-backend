"""Adding project and project_run tables

Revision ID: a516a38633f3
Revises: 311cbfb40a98
Create Date: 2024-10-21 16:06:04.575148

"""

from typing import Sequence, Union
from sqlalchemy.sql import func

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a516a38633f3"
down_revision: Union[str, None] = "311cbfb40a98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            nullable=False,
            primary_key=True,
        ),
        sa.Column("name", sa.VARCHAR(), nullable=False),
        sa.Column("description", sa.VARCHAR()),
        sa.Column("created_by", sa.VARCHAR(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=func.now(),
        ),
        sa.Column(
            "is_active",
            sa.BOOLEAN(),
            nullable=False,
            default=True,
            server_default="true",
        ),
        sa.Column("attributes", sa.JSON(), default=True),
        sa.PrimaryKeyConstraint(name="project_pk"),
    )
    op.create_table(
        "project_run",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            nullable=False,
            primary_key=True,
        ),
        sa.Column("name", sa.VARCHAR(), nullable=True),
        sa.Column("run_type", sa.VARCHAR(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=func.now(),
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(),
            nullable=False,
            server_default=func.now(),
        ),
        sa.Column(
            "is_active",
            sa.BOOLEAN(),
            nullable=False,
            default=True,
            server_default="true",
        ),
        sa.Column("project_id", sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["project.id"], name="project_run_project_id_fkey"
        ),
        sa.PrimaryKeyConstraint(name="project_run_pk"),
    )


def downgrade() -> None:
    op.drop_table("project_run")
    op.drop_table("project")
