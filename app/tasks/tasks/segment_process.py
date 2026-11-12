import uuid

from sqlmodel import Session

from app.db.models.task import (
    TaskDb,
    TaskStepDb,
    TaskStepInsert,
    TaskStatusEnum,
)

from app.repository.task_repository import TaskRepository
from app.repository.task_step_repository import TaskStepRepository

from app.helpers.path_helper import (
    create_task_step_input_path,
    get_files_from_path_with_extension,
    create_task_step_output_path,
    merge_path_with_extra_folder,
    create_extra_folder_for_interface,
)

from app.tasks import logger
from .task_base import get_previous_task
from .task_validate import TaskValidation


def segment_process(task: TaskDb, session: Session) -> list[TaskStepDb]:
    from app.container import Container
    task_repository = Container.task_repository()
    task_repository.set_session(session)
    task_step_repository = Container.task_step_repository()
    task_step_repository.set_session(session)

    return SegmentProcess.handle(task, task_repository, task_step_repository)


class SegmentProcess:
    @staticmethod
    def handle(task: TaskDb, task_repository: TaskRepository,
            task_step_repository: TaskStepRepository,
            previous_task_id: int = 0) -> list[TaskStepDb]:
        """
        Get the previous task step (tile images)
        Get all the times as paths
        create 1 step per tile per interface in the attributes.interface_to_use list
        set them all to  QUEUED
        return them all
        """

        previous_task = get_previous_task(task, task_repository, previous_task_id)

        # get all the steps which are finished
        finished_steps = TaskValidation.get_successful_steps(previous_task)

        if not finished_steps:
            logger.error("No finished steps found for previous task. Killing the run")
            # mark task as failed
            task.status = TaskStatusEnum.ERROR
            # mark next steps as failed or killed
            return []

        # there is just one finished step
        tiling_step = finished_steps[0]

        tiling_output_path = tiling_step.output_path
        image_files_to_segment = get_files_from_path_with_extension(
            tiling_output_path, "tif"
        )
        steps = []
        for interface_id in task.attributes["interface_to_use"]:
            input_path = create_extra_folder_for_interface(
                task.input_path, interface_id
            )
            for image_file in image_files_to_segment:
                step_to_insert = TaskStepInsert(
                    task_id=task.id,
                    task_type_id=task.task_type_id,
                    interface_id=interface_id,
                    status=TaskStatusEnum.QUEUED,
                    external_id=uuid.uuid4(),
                    input_path=input_path,
                )

                step_added = task_step_repository.create(step_to_insert)
                logger.info(f"Step [segment_process] added with id: {step_added}")

                # create the work areas (paths)
                step_added.input_path = create_task_step_input_path(step_added)
                step_added.output_path = create_task_step_output_path(
                    step_added
                )
                # set the real input path (the image path)
                step_added.input_path = merge_path_with_extra_folder(
                    tiling_output_path, image_file
                )

                steps.append(step_added)

        return steps
