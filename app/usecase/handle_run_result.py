from datetime import datetime
from pathlib import Path
from uuid import UUID
from contextlib import AbstractContextManager
from typing import Callable

from sqlmodel import Session

from . import logger

from app.repository.task_repository import TaskRepository
from app.repository.task_step_repository import TaskStepRepository

from app.db.models.task import TaskStepResultInsert, TaskStatusEnum, TaskStepDb


def get_new_file_name(task_step: TaskStepDb, task_step_result: TaskStepResultInsert) -> (bool, str):
    task_type_name = task_step.task.task_type.name

    #if task_type_name == 'TileImagesSrc':
    #    return True, "tile"
    if task_type_name == 'SegmentProcess':
        class_name = 'unknown'
        if 'segmentation-type' in task_step_result.additional_info:
            class_name = task_step_result.additional_info['segmentation-type']
        return True, f"seg_{class_name}"

    return False, "unknown"


def update_output_file_name(task_step, task_step_result):
    # get files from output folder
    # get the first part of the name of the file, split on '__'
    # call method to get proper name based on the task_step.type
    # rename the first part of the file with the new name
    # done

    should_rename, rename_with = get_new_file_name(task_step, task_step_result)
    if not should_rename:
        return

    output_path = Path(task_step.output_path)
    for file in output_path.iterdir():
        first_part_of_name = file.name.split('__')[0]
        new_name = file.name.replace(first_part_of_name, rename_with)
        logger.info("Renaming file: " + file.name + " to: " + new_name)
        file.rename(output_path / new_name)


class HandleRunResultUseCase:
    def __init__(
        self,
        session_factory: Callable[..., AbstractContextManager[Session]],
        task_repository: TaskRepository,
        task_step_repository: TaskStepRepository,
    ) -> None:
        self.session_factory = session_factory
        self.task_repository = task_repository
        self.task_step_repository = task_step_repository

    def handle(
        self, step_external_id: UUID, step_result: TaskStepResultInsert
    ) -> bool:
        with self.session_factory() as session:
            self.task_repository.set_session(session)
            self.task_step_repository.set_session(session)
            result = self._handle(step_external_id, step_result, session)
            return result

    def _handle(
        self, step_external_id: UUID, step_result: TaskStepResultInsert, session
    ) -> bool:
        task_step = self.task_step_repository.get_by_external_id(
            step_external_id
        )
        if task_step is None:
            logger.error(
                f"Task step with external_id {step_external_id} not found"
            )
            return False

        if task_step.status != TaskStatusEnum.RUNNING:
            logger.error(
                f"Task step with external_id {step_external_id} is not running. It's status is {task_step.status}"
            )
            return False

        if step_result.success:
            logger.info(f"Task step with external_id {step_external_id} finished successfully")
        else:
            logger.error(
                f"Task step with external_id {step_external_id} finished with error: {step_result}"
            )

        # inserting the result to the db
        task_step.finished_at = datetime.now()
        task_step.status = TaskStatusEnum.FINISHED if step_result.success else TaskStatusEnum.ERROR
        step_result.task_step_id = task_step.id
        self.task_step_repository.save_answer(step_result)

        # update the output file name if needed
        if task_step.status == TaskStatusEnum.FINISHED:
            update_output_file_name(task_step, step_result)

        # check if the task has more steps to run
        has_steps_pending = self.task_step_repository.has_steps_pending(
            task_step.task_id
        )

        if not has_steps_pending:
            # if no more steps to run, the task is finished
            task = self.task_repository.get_by_id(task_step.task_id)
            task.finished_at = datetime.now()
            task.status = TaskStatusEnum.FINISHED

        session.commit()
        return True
