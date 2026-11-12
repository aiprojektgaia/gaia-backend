from app.tasks.task_runner import (
    build_default_args,
    execute_model,
    set_task_step_as_failed,
)
from .constants import logger

import traceback
from datetime import datetime
from app.config import get_callback_url
from app.container import Container
from app.db.models.task import TaskStatusEnum
from app.service.interface_service import InterfaceService
from .step_base import update_required_arguments


async def vectorize_tile_result(task_step_id: int):
    try:
        session_factory = Container.session_factory()
        task_step_repository = Container.task_step_repository()
        #task_repository = Container.task_repository()
        interface_repository = Container.interface_repository()

        with session_factory() as session:
            task_step_repository.set_session(session)
            task_step = task_step_repository.get_by_id(task_step_id)
            task_step.status = TaskStatusEnum.RUNNING
            task_step.started_at = datetime.now()

            #task_repository.set_session(session)
            #task = task_repository.get_by_id(task_step.task_id)

            # get the associated interface from the database
            interface_repository.set_session(session)
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

        # Get the attributes containing project_run specific arguments for this run
        # and get the default arguments for
        args_to_add = update_required_arguments(interface.args, {}, default_args)
        interface.args.update(args_to_add)

        logger.info(
            f"Running 'vectorise image result' for task with id: {task_step.id}"
        )
        await execute_model(interface, task_step_id, {})

    except Exception as e:
        logger.error(f"Error vectorizing image result: {e}")
        logger.error(traceback.format_exc())
        set_task_step_as_failed(task_step_id)
