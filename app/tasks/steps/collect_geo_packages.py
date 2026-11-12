import traceback
from pathlib import Path

from app.container import Container
from app.db.models.task import TaskStatusEnum, TaskStepResultInsert

from .constants import logger

'''
NOTE. The idea for this step is to not only gather all the geo-packages
but to also read them and create one geo-package which will be the final output of the task.
To achieve that, it needs to read all the packages and then merge them, probably even run
a union process in case some of the results intersect each other.

For the time being, it will just dump all results into a single folder.
And that is why it looks to similar to the collect_segmentation_tiles.py
'''

async def collect_geo_packages(task_step_id: int):
    try:
        session_factory = Container.session_factory()
        task_step_repository = Container.task_step_repository()
        with session_factory() as session:
            task_step_repository.set_session(session)

            task_step = task_step_repository.get_by_id(task_step_id)
            task_step.status = TaskStatusEnum.RUNNING
            logger.debug(f"MergeGeoPackages, task with id: {task_step.id} started")

            session.expire_on_commit = False
            session.commit()

        total_moved = move_files_to_output_path(task_step)
        logger.info(f"Moved {total_moved} files to output path ({task_step.output_path})")

        with session_factory() as session:
            task_step_repository.set_session(session)

            task_step = task_step_repository.get_by_id(task_step_id)
            task_step.status = TaskStatusEnum.FINISHED
            logger.debug(f"MergeGeoPackages, task with id: {task_step.id} finished")

        result_use_case = Container.handle_run_result_usecase()
        result_use_case.handle(
            task_step.external_id,
            TaskStepResultInsert(
                success=True,
                error={},
                additional_info={
                    "message": "The merging of geo packages really worked",
                    "total_moved": total_moved
                },
            ),
        )

    except Exception as e:
        logger.error(f"Error Merging GeoPackages: {e}")
        logger.error(traceback.format_exc())

def move_files_to_output_path(task_step) -> int:
    # the input path is the base path for the segmentation process and should
    # contain all subfolders with the result tiles
    input_path = Path(task_step.input_path)

    output_path = Path(task_step.output_path)
    counter = 0
    for file in input_path.iterdir():
        file.rename(output_path / file.name)
        counter += 1

    return counter
