"""adding interface tables

Revision ID: 2841b1f32f5f
Revises: a516a38633f3
Create Date: 2024-10-23 11:03:37.629108

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2841b1f32f5f"
down_revision: Union[str, None] = "a516a38633f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interface_group",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("name", sa.VARCHAR(), nullable=False),
        sa.PrimaryKeyConstraint(name="interface_group_pk"),
    )

    op.create_table(
        "interface",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("name", sa.VARCHAR(), nullable=False),
        sa.Column("interface_group_id", sa.INTEGER(), nullable=False),
        sa.Column("description", sa.VARCHAR(), nullable=True),
        sa.Column("path", sa.VARCHAR(), nullable=True),
        sa.Column("is_active", sa.BOOLEAN(), nullable=False, default=True, server_default="true"),
        sa.Column("args", sa.JSON(), nullable=True),
        sa.Column("module_file_name", sa.VARCHAR(), nullable=False),
        sa.Column("function_name", sa.VARCHAR(), nullable=False),
        sa.Column("venv_path", sa.VARCHAR(), nullable=True, default=None),
        sa.Column("installed", sa.BOOLEAN(), nullable=False, default=False, server_default="false"),
        sa.PrimaryKeyConstraint(name="interface_pk"),
        sa.ForeignKeyConstraint(
            ["interface_group_id"], ["interface_group.id"], name="interface_interface_group_id_fkey"
        ),
    )

    op.create_table(
        "run_type",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("name", sa.VARCHAR(), nullable=False),
        sa.PrimaryKeyConstraint(name="run_type_pk"),
    )

    op.add_column(
        "project_run",
        sa.Column(
            "run_type_id",
            sa.INTEGER(),
            sa.ForeignKey("run_type.id", name="project_run_run_type_id_fkey"),
            nullable=True,
        ),
    )
    op.add_column("project_run", sa.Column("input_path", sa.VARCHAR(), nullable=True))
    op.add_column("project_run", sa.Column("output_path", sa.VARCHAR(), nullable=True))
    op.add_column("project_run", sa.Column("attributes", sa.JSON(), nullable=True))

    # inserts
    op.execute("insert into interface_group (name) values ('Classification')")

    op.execute("insert into run_type (name) values ('SegmentArea')")
    op.execute("insert into run_type (name) values ('CompareToBaseImage')")
    op.execute("insert into run_type (name) values ('Vectorize')")


def downgrade() -> None:
    op.drop_column("project_run", "attributes")
    op.drop_column("project_run", "output_path")
    op.drop_column("project_run", "input_path")
    op.drop_column("project_run", "run_type_id")
    op.drop_table("run_type")

    op.drop_table("interface")
    op.drop_table("interface_group")
