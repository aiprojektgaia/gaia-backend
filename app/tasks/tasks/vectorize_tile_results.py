import uuid

from sqlmodel import Session

from app.db.models.task import TaskDb, TaskStepDb, TaskStepInsert, TaskStatusEnum
from app.repository.interface_repository import InterfaceRepository

from app.repository.task_repository import TaskRepository
from app.repository.task_step_repository import TaskStepRepository

from app.helpers.path_helper import (
    create_task_step_input_path,
    get_files_from_path_with_extension,
    create_task_step_output_path,
    merge_path_with_extra_folder,
)
from app.tasks import logger
from app.tasks.tasks.task_base import get_previous_task


def vectorize_tile_results(task: TaskDb, session: Session, previous_task_id: int = 0) -> list[TaskStepDb]:
    from app.container import Container
    task_repository = Container.task_repository()
    task_repository.set_session(session)
    task_step_repository = Container.task_step_repository()
    task_step_repository.set_session(session)
    interface_repository = Container.interface_repository()
    interface_repository.set_session(session)

    return VectorizeTileResult.handler(task, task_repository, task_step_repository,
                                       interface_repository, previous_task_id)


def get_interface_to_use(task, interface_repository):
    search_key = "classname"
    parent_interface = interface_repository.get(task.interface_id)
    class_name = parent_interface.args.get(search_key, "buildings")

    interface_group_name = "Vectorization"
    interfaces = interface_repository.get_by_group_name(interface_group_name)
    for interface in interfaces:
        if interface.args.get(search_key, "?") == class_name:
            return interface

    return None


class VectorizeTileResult:
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


        interface = get_interface_to_use(task, interface_repository)

        steps = []
        for step in finished_steps:
            images_files_to_vectorize = get_files_from_path_with_extension(
                step.output_path, "tif"
            )
            for image_file in images_files_to_vectorize:
                step_to_insert = TaskStepInsert(
                    task_id=task.id,
                    task_type_id=task.task_type_id,
                    interface_id=interface.id,
                    status=TaskStatusEnum.QUEUED,
                    external_id=uuid.uuid4(),
                    input_path=task.input_path
                )

                step_added = task_step_repository.create(step_to_insert)
                logger.info(f"Step [vectorize_tile_results] added with id: {step_added}")

                step_added.input_path = create_task_step_input_path(step_added)
                step_added.output_path = create_task_step_output_path(step_added)

                # set the real input path (the image path)
                step_added.input_path = merge_path_with_extra_folder(
                    step.output_path, image_file
                )

                steps.append(step_added)

        return steps
