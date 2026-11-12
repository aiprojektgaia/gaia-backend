"""adding task tables

Revision ID: 74b192026e9c
Revises: 2841b1f32f5f
Create Date: 2024-10-23 11:23:23.952221

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "74b192026e9c"
down_revision: Union[str, None] = "2841b1f32f5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_type",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            nullable=False,
            primary_key=True,
        ),
        sa.Column("name", sa.VARCHAR(), nullable=False),
        sa.Column("run_type_id", sa.INTEGER(), nullable=False),
        sa.Column("order", sa.INTEGER(), nullable=False),
        sa.PrimaryKeyConstraint(name="task_type_pk"),
        sa.ForeignKeyConstraint(
            ["run_type_id"], ["run_type.id"], name="task_type_run_type_id_fkey"
        ),
    )

    op.create_table(
        "task",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            nullable=False,
            primary_key=True,
        ),
        sa.Column("project_run_id", sa.INTEGER(), nullable=False),
        sa.Column("task_type_id", sa.INTEGER(), nullable=False),
        sa.Column("interface_id", sa.INTEGER(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("finished_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("status", sa.VARCHAR(), nullable=True, default=0),
        sa.Column("input_path", sa.VARCHAR(), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint(name="task_pk"),
        sa.ForeignKeyConstraint(
            ["project_run_id"],
            ["project_run.id"],
            name="task_project_run_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["task_type_id"], ["task_type.id"], name="task_task_type_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["interface_id"], ["interface.id"], name="task_interface_id_fkey"
        ),
    )

    op.create_table(
        "task_step",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            nullable=False,
            primary_key=True,
        ),
        sa.Column("task_id", sa.INTEGER(), nullable=False),
        sa.Column("task_type_id", sa.INTEGER(), nullable=False),  # just info
        sa.Column("interface_id", sa.INTEGER(), nullable=True),  # just info
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("finished_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("input_path", sa.VARCHAR(), nullable=True),
        sa.Column("output_path", sa.VARCHAR(), nullable=True),
        sa.PrimaryKeyConstraint(name="task_step_pk"),
        sa.ForeignKeyConstraint(
            ["task_id"], ["task.id"], name="task_task_id_fkey"
        ),
    )

    op.create_table(
        "task_step_result",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            nullable=False,
            primary_key=True,
        ),
        sa.Column("task_step_id", sa.INTEGER(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("success", sa.BOOLEAN(), nullable=False, default=False),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("additional_info", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint(name="task_result_pk"),
        sa.ForeignKeyConstraint(
            ["task_step_id"],
            ["task_step.id"],
            name="task_result_task_step_id_fkey",
        ),
    )

    # insert default run and task types
    # Just Segmentation
    op.execute("""
DO $$
DECLARE 
    runId int := 0;
    orderNum int := 1;

BEGIN
    select id into runId 
    from run_type rt 
    where rt.name = 'SegmentArea';

    INSERT INTO task_type(name, run_type_id, "order")
    VALUES('TileImagesSrc', runId, orderNum);
    orderNum := orderNum + 1;

    INSERT INTO task_type(name, run_type_id, "order")
    VALUES('SegmentProcess', runId, orderNum);
    orderNum := orderNum + 1;

    INSERT INTO task_type(name, run_type_id, "order")
    VALUES('MergeTiles', runId, orderNum);
END $$;

""")

    # Image comparison
    op.execute("""
DO $$
DECLARE 
    runId int := 0;
    orderNum int := 1;

BEGIN
    select id into runId 
    from run_type rt 
    where rt.name = 'CompareToBaseImage';

    INSERT INTO task_type(name, run_type_id, "order")
    VALUES('TileImagesSrc', runId, orderNum);
    orderNum := orderNum + 1;

    INSERT INTO task_type(name, run_type_id, "order")
    VALUES('Vector2Raster', runId, orderNum);
    orderNum := orderNum + 1;

    INSERT INTO task_type(name, run_type_id, "order")
    VALUES('TileImagesBase', runId, orderNum);
    orderNum := orderNum + 1;

    INSERT INTO task_type(name, run_type_id, "order")
    VALUES('SegmentProcessSrc', runId, orderNum);
    orderNum := orderNum + 1;

    INSERT INTO task_type(name, run_type_id, "order")
    VALUES('SegmentProcessBase', runId, orderNum);
    orderNum := orderNum + 1;

    INSERT INTO task_type(name, run_type_id, "order")
    VALUES('MergeTilesSrc', runId, orderNum);
    orderNum := orderNum + 1;

    INSERT INTO task_type(name, run_type_id, "order")
    VALUES('MergeTilesBase', runId, orderNum);
END $$;
""")

    # Vectorize
    op.execute("""
DO $$
DECLARE 
    runId int := 0;
    orderNum int := 1;

BEGIN
    select id into runId 
    from run_type rt 
    where rt.name = 'Vectorize';

    INSERT INTO task_type(name, run_type_id, "order")
    VALUES('ToVector', runId, orderNum);
END $$;
""")


def downgrade() -> None:
    op.drop_table("task_step_result")
    op.drop_table("task_step")
    op.drop_table("task")
    op.drop_table("task_type")
