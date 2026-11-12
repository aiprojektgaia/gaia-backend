import uuid

from sqlmodel import Session

from app.config import get_config
from app.db.models.task import TaskDb, TaskStepDb, TaskStepInsert, TaskStatusEnum
from app.repository.interface_repository import InterfaceRepository

from app.repository.task_repository import TaskRepository
from app.repository.task_step_repository import TaskStepRepository

from app.helpers.path_helper import (
    create_task_step_input_path,
    create_task_step_output_path,
)
from app.tasks import logger
from app.tasks.tasks.task_base import get_previous_task


def apply_confidence(task: TaskDb, session: Session, previous_task_id: int = 0) -> list[TaskStepDb]:
    from app.container import Container
    task_repository = Container.task_repository()
    task_repository.set_session(session)
    task_step_repository = Container.task_step_repository()
    task_step_repository.set_session(session)
    interface_repository = Container.interface_repository()
    interface_repository.set_session(session)

    return ApplyConfidence.handler(task, task_repository, task_step_repository,
                                   interface_repository, previous_task_id)

class ApplyConfidence:
    @staticmethod
    def handler(task: TaskDb, task_repository: TaskRepository,
                task_step_repository: TaskStepRepository,
                interface_repository: InterfaceRepository,
                previous_task_id: int = 0) -> list[TaskStepDb]:
        """
        Get the previous task (segmentation process)
        Create 1 step per interface in the attributes.interface_to_use list
        Per step, create a new step which should vectorize the result image
        """

        previous_task = get_previous_task(task, task_repository, previous_task_id)

        # get all the steps which are finished
        finished_steps = [s for s in previous_task.steps if s.status == TaskStatusEnum.FINISHED]
        # Note: this could cause an error, if all children failed => how should this work?
        if not finished_steps:
            logger.error("No finished steps found for previous task. Killing the run")
            # mark task as failed
            task.status = TaskStatusEnum.ERROR
            # mark next steps as failed or killed
            return []

        interface_name = get_config().DEFAULT_IMAGE_TO_BIT_INTERFACE_NAME
        interface = interface_repository.get_by_name(interface_name)

        steps = []
        for previous_step in finished_steps:
            step_to_insert = TaskStepInsert(
                task_id=task.id,
                task_type_id=task.task_type_id,
                interface_id=interface.id,
                status=TaskStatusEnum.QUEUED,
                external_id=uuid.uuid4(),
                input_path=task.input_path
            )

            step_added = task_step_repository.create(step_to_insert)

            step_added.input_path = create_task_step_input_path(step_added)
            step_added.output_path = create_task_step_output_path(step_added)

            # the input path is the previous set output path
            logger.debug(f"[bitter] previous-step: id ({previous_step.id}) and output_path: {previous_step.output_path}")
            step_added.input_path = previous_step.output_path
            logger.debug(f"Step [bitter] added with id: {step_added}")

            steps.append(step_added)

        return steps
