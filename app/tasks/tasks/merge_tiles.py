import uuid

from sqlmodel import Session

from app.db.models.task import TaskDb, TaskStepDb, TaskStepInsert, TaskStatusEnum

from app.repository.task_repository import TaskRepository
from app.repository.task_step_repository import TaskStepRepository

from app.helpers.path_helper import create_task_step_input_path, \
    create_task_step_output_path, create_extra_folder_for_interface

from app.tasks import logger
from .task_base import get_previous_task
from .task_validate import TaskValidation


def merge_tiles(task: TaskDb, session: Session) -> list[TaskStepDb]:
    from app.container import Container
    task_repository = Container.task_repository()
    task_repository.set_session(session)
    task_step_repository = Container.task_step_repository()
    task_step_repository.set_session(session)

    return MergeTiles.handler(task, task_repository, task_step_repository)

class MergeTiles:
    @staticmethod
    def handler(task: TaskDb, task_repository: TaskRepository,
                task_step_repository: TaskStepRepository,
                previous_task_id: int = 0) -> list[TaskStepDb]:
        """
        Get the previous task (segmentation process)
        Create 1 step per interface in the attributes.interface_to_use list
        Each step should "just" move the result tiles from the segmentation process for that specific interface
        to its own unified location.
        that location will then be used for the next step (vectorization)
        """
        # this part should probably be done when running each of the steps created.
        # or at least part of them.

        previous_task = get_previous_task(task, task_repository, previous_task_id)

        # get all the steps which are finished
        finished_steps = TaskValidation.get_successful_steps(previous_task)
        if not finished_steps:
            logger.error("No finished steps found for previous task. Killing the run")
            # mark task as failed
            task.status = TaskStatusEnum.ERROR
            # mark next steps as failed or killed
            return []

        steps = []
        for interface_id in task.attributes["interface_to_use"]:
            step_to_insert = TaskStepInsert(
                task_id=task.id,
                task_type_id=task.task_type_id,
                interface_id=interface_id,
                status=TaskStatusEnum.QUEUED,
                external_id=uuid.uuid4(),
                input_path=task.input_path
            )

            step_added = task_step_repository.create(step_to_insert)
            logger.info(f"Step [merge_tiles] added with id: {step_added}")

            step_added.input_path = create_task_step_input_path(step_added)
            step_added.output_path = create_task_step_output_path(step_added)

            # Note. A better way might be to add all the segmented step paths with status FINISHED
            # to this step, so the step just moves the images/files to its output folder

            # read input path is the segmentation per interface path
            step_added.input_path = create_extra_folder_for_interface(
                previous_task.input_path, interface_id)

            steps.append(step_added)

        return steps
