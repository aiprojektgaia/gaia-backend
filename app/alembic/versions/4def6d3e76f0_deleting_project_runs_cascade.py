"""deleting project runs cascade

Revision ID: 4def6d3e76f0
Revises: c2ed5aafe1a5
Create Date: 2025-03-24 16:32:31.547279

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4def6d3e76f0'
down_revision: Union[str, None] = 'c2ed5aafe1a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.execute("""
        ALTER TABLE task_step_result
            DROP CONSTRAINT task_result_task_step_id_fkey,
            ADD  CONSTRAINT task_result_task_step_id_fkey FOREIGN KEY (task_step_id)
                REFERENCES task_step (id) MATCH SIMPLE
                ON DELETE CASCADE
        ; 
    """)

    op.execute("""
        ALTER TABLE task_step
            DROP CONSTRAINT task_task_id_fkey,
            ADD  CONSTRAINT task_task_id_fkey FOREIGN KEY (task_id)
                REFERENCES task (id) MATCH SIMPLE
                ON DELETE CASCADE
        ;
    """)

    op.execute("""
        ALTER TABLE task
            DROP CONSTRAINT task_project_run_id_fkey,
            ADD  CONSTRAINT task_project_run_id_fkey FOREIGN KEY (project_run_id)
                REFERENCES project_run (id) MATCH SIMPLE
                ON DELETE CASCADE
        ;
    """)

    op.execute("""
        ALTER TABLE task_type
            DROP CONSTRAINT task_type_run_type_id_fkey,
            ADD  CONSTRAINT task_type_run_type_id_fkey FOREIGN KEY (run_type_id)
                REFERENCES run_type (id) MATCH SIMPLE
                ON DELETE CASCADE
        ;
    """)


def downgrade() -> None:

    op.execute("""
        ALTER TABLE task_step_result
            DROP CONSTRAINT task_result_task_step_id_fkey,
            ADD  CONSTRAINT task_result_task_step_id_fkey FOREIGN KEY (task_step_id)
                REFERENCES task_step (id) MATCH SIMPLE
        ; 
    """)

    op.execute("""
        ALTER TABLE task_step
            DROP CONSTRAINT task_task_id_fkey,
            ADD  CONSTRAINT task_task_id_fkey FOREIGN KEY (task_id)
                REFERENCES task (id) MATCH SIMPLE
        ;
    """)

    op.execute("""
        ALTER TABLE task
            DROP CONSTRAINT task_project_run_id_fkey,
            ADD  CONSTRAINT task_project_run_id_fkey FOREIGN KEY (project_run_id)
                REFERENCES project_run (id) MATCH SIMPLE
        ;
    """)

    op.execute("""
        ALTER TABLE task_type
            DROP CONSTRAINT task_type_run_type_id_fkey,
            ADD  CONSTRAINT task_type_run_type_id_fkey FOREIGN KEY (run_type_id)
                REFERENCES run_type (id) MATCH SIMPLE
        ;
    """)
