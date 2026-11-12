"""Adding runType RunItAll

Revision ID: c2ed5aafe1a5
Revises: c06243228330
Create Date: 2025-02-17 14:53:12.757051

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c2ed5aafe1a5'
down_revision: Union[str, None] = 'c06243228330'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    DO $$ 
    declare runTypeId integer;
    BEGIN
        insert into run_type(name) VALUES('RunItAll') RETURNING id INTO runTypeId;
    
        insert into task_type(name, run_type_id, "order", is_interface_dependent) values('TileImagesSrc',    runTypeId, 1, False);
        insert into task_type(name, run_type_id, "order", is_interface_dependent) values('SegmentProcess',   runTypeId, 2, True);
        insert into task_type(name, run_type_id, "order", is_interface_dependent) values('MergeTiles',       runTypeId, 3, True);
        insert into task_type(name, run_type_id, "order", is_interface_dependent) values('ApplyConfidence',  runTypeId, 4, True);
        insert into task_type(name, run_type_id, "order", is_interface_dependent) values('Vectorize',        runTypeId, 5, True);
        insert into task_type(name, run_type_id, "order", is_interface_dependent) values('MergeGeoPackages', runTypeId, 6, True);
    
    END $$ 
    """)


def downgrade() -> None:

    op.execute("""
               DELETE FROM task_type WHERE run_type_id IN (SELECT id FROM run_type WHERE name = 'RunItAll');
               """)

    op.execute("""
               DELETE FROM run_type WHERE name = 'RunItAll';
               """)
