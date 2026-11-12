import uuid

from sqlmodel import Session

from app.db.models.task import TaskDb, TaskStepDb, TaskStepInsert, TaskStatusEnum

from app.repository.interface_repository import InterfaceRepository
from app.repository.task_step_repository import TaskStepRepository

from app.helpers.path_helper import create_task_step_input_path, create_task_step_output_path

from app.tasks import logger
from app.config import get_config

def tile_image(task: TaskDb, session: Session) -> list[TaskStepDb]:
    from app.container import Container
    interface_repository = Container.interface_repository()
    interface_repository.set_session(session)
    task_step_repository = Container.task_step_repository()
    task_step_repository.set_session(session)

    return ImageTiler.handle(task, interface_repository, task_step_repository)

class ImageTiler:
    @staticmethod
    def handle(task: TaskDb, interface_repository: InterfaceRepository,
               task_step_repository: TaskStepRepository) -> list[TaskStepDb]:
        """
        Get the model which runs image tiling
        create 1 step which sets that interface with the correct system paths
        return a new TaskStep
        """

        image_tiler_interface_name = get_config().DEFAULT_IMAGE_TILER_INTERFACE_NAME
        interface = interface_repository.get_by_name(image_tiler_interface_name)
        if interface is None:
            logger.error("ImageTiles interface not found")
            raise Exception("ImageTiles interface not found")

        step_to_insert = TaskStepInsert(
            task_id=task.id,
            task_type_id=task.task_type_id,
            interface_id=interface.id,
            status=TaskStatusEnum.QUEUED,
            external_id=uuid.uuid4(),
            input_path=task.input_path
        )

        step_added = task_step_repository.create(step_to_insert)
        logger.info(f"Task [time_image] added with id: {step_added}")

        # NOTE: is the input_path where the initial big image block should be added
        step_added.input_path = create_task_step_input_path(step_added)
        # the output path is where all the created tiles will be added
        step_added.output_path = create_task_step_output_path(step_added)

        return [step_added]
