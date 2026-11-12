from datetime import datetime

from app.tasks.task_runner import (
    build_default_args,
    execute_model,
    set_task_step_as_failed,
)
from .constants import logger

import traceback
from app.config import get_callback_url
from app.container import Container
from app.db.models.task import TaskStatusEnum
from app.service.interface_service import InterfaceService
from .step_base import update_required_arguments


# async def TileImagesSrc(task_step_id: int):
async def to_bit_image(task_step_id: int):
    try:
        logger.info(f"From segmentation results to one big bit image for task with id: {task_step_id}")
        session_factory = Container.session_factory()
        task_step_repository = Container.task_step_repository()
        task_repository = Container.task_repository()
        interface_repository = Container.interface_repository()

        with session_factory() as session:
            # set up connection to the database
            task_step_repository.set_session(session)
            interface_repository.set_session(session)
            task_repository.set_session(session)

            # get the task step from the database
            task_step = task_step_repository.get_by_id(task_step_id)
            task_step.status = TaskStatusEnum.RUNNING
            task_step.started_at = datetime.now()

            task = task_repository.get_by_id(task_step.task_id)

            interface = interface_repository.get(task_step.interface_id)

            session.expire_on_commit = False
            session.commit()

        if interface is None:
            raise ValueError(
                f"No interface found for task step with id: {task_step_id}"
            )

        InterfaceService.is_interface_runnable(interface)
        default_args = build_default_args(
            callback_url=get_callback_url(task_step.external_id),
            output_path=task_step.output_path,
            image_path=task_step.input_path,
        )

        args_to_add = update_required_arguments(interface.args, task.attributes, default_args)
        # Good, bad, ugly?
        # I am doing this since the runner uses the interface args together with the extra arguments
        interface.args.update(args_to_add)
        logger.info(
            f"Running 'to_big_bit_image' for task with id: {task_step.id}"
        )
        await execute_model(interface, task_step_id, {})

    except Exception as e:
        logger.error(f"Error while creating a bit image: {e}")
        logger.error(traceback.format_exc())
        set_task_step_as_failed(task_step_id)
