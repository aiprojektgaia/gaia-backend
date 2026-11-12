import uuid

from sqlmodel import Session

from app.db.models.task import TaskDb, TaskStepDb, TaskStepInsert, TaskStatusEnum

from app.repository.task_repository import TaskRepository
from app.repository.task_step_repository import TaskStepRepository

from app.helpers.path_helper import create_extra_folder_for_interface, \
    create_output_path

from app.tasks import logger
from .task_base import get_previous_task
from .task_validate import TaskValidation


def merge_geo_packages(task: TaskDb, session: Session, previous_task_id: int = 0) -> list[TaskStepDb]:
    from app.container import Container
    task_repository = Container.task_repository()
    task_repository.set_session(session)
    task_step_repository = Container.task_step_repository()
    task_step_repository.set_session(session)

    return MergePackages.handler(task, task_repository, task_step_repository, previous_task_id)

class MergePackages:
    @staticmethod
    def handler(task: TaskDb, task_repository: TaskRepository,
                task_step_repository: TaskStepRepository,
                previous_task_id: int = 0) -> list[TaskStepDb]:
        """
        Get the previous task (vectorization process)
        Create 1 step per interface
        Each step should "just" move the result tiles from the vectorization process for that specific interface
        to its own unified location.
        """

        previous_task = get_previous_task(task, task_repository, previous_task_id)

        finished_steps = TaskValidation.get_successful_steps(previous_task)
        if not finished_steps:
            logger.error("No finished steps found for previous task. Killing the run")
            # mark task as failed
            task.status = TaskStatusEnum.ERROR
            # mark next steps as failed or killed
            return []

        previous_output_paths = finished_steps[0].output_path

        step_to_insert = TaskStepInsert(
            task_id=task.id,
            task_type_id=task.task_type_id,
            interface_id=task.interface_id,
            status=TaskStatusEnum.QUEUED,
            external_id=uuid.uuid4(),
            input_path=task.input_path
        )

        step_added = task_step_repository.create(step_to_insert)
        logger.info(f"Step [merge_geo_packages] added with id: {step_added}")

        step_added.input_path = previous_output_paths
        # output is
        step_added.output_path = create_output_path(task.input_path)
        step_added.output_path = create_extra_folder_for_interface(step_added.output_path, task.interface_id)

        return [step_added]
