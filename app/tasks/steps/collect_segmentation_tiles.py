import traceback
from datetime import datetime
from pathlib import Path

from app.container import Container
from app.db.models.task import TaskStatusEnum, TaskStepResultInsert

from .constants import logger

#async def MergeTiles(task_step_id: int):

async def collect_segmentation_tiles(task_step_id: int):
    try:
        session_factory = Container.session_factory()
        task_step_repository = Container.task_step_repository()
        with session_factory() as session:
            task_step_repository.set_session(session)

            task_step = task_step_repository.get_by_id(task_step_id)
            task_step.status = TaskStatusEnum.RUNNING
            task_step.started_at = datetime.now()
            logger.debug(f"MergeTiles, task with id: {task_step.id} started")

            session.expire_on_commit = False
            session.commit()

        total_moved = move_files_to_output_path(task_step)
        logger.info(f"Moved {total_moved} files to output path ({task_step.output_path})")

        with session_factory() as session:
            task_step_repository.set_session(session)

            task_step = task_step_repository.get_by_id(task_step_id)
            task_step.status = TaskStatusEnum.FINISHED
            logger.debug(f"MergeTiles, task with id: {task_step.id} finished")

        result_use_case = Container.handle_run_result_usecase()
        result_use_case.handle(
            task_step.external_id,
            TaskStepResultInsert(
                success=True,
                error={},
                additional_info={
                    "message": "The merging of tiles definitely worked",
                    "total_moved": total_moved
                },
            ),
        )

    except Exception as e:
        logger.error(f"Error Merging tiles: {e}")
        logger.error(traceback.format_exc())

def move_files_to_output_path(task_step) -> int:
    # the input path is the base path for the segmentation process and should
    # contain all subfolders with the result tiles
    input_path = Path(task_step.input_path)

    # list all subfolders in the input path
    subfolders = [f for f in input_path.iterdir() if f.is_dir()]
    # for each subfolder, move all files to the output path
    output_path = Path(task_step.output_path)
    counter = 0
    for subfolder in subfolders:
        out_folder = subfolder / "output"
        for file in out_folder.iterdir():
            file.rename(output_path / file.name)
            counter += 1

    # making things up, this might what we actually need, but for now, let's keep it simple
    # for each subfolder, move all files with extension png to the output path
    #for subfolder in subfolders:
    #    for file in subfolder.iterdir():
    #        if file.suffix == ".png":
    #            file.rename(task_step.output_path / file.name)

    return counter