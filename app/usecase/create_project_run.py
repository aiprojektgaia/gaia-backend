from contextlib import AbstractContextManager
from typing import Callable, Any

from sqlmodel import Session

from . import logger
from app.config import get_config
from app.helpers.wms_policy import validate_wms_url
from app.db.models.project import ProjectRunDb, ProjectRunInsert
from app.db.models.task import (
    TaskInsert,
    RunType,
    TaskStatusEnum,
)
from app.db.models.project import RunTypesEnum
from app.repository.project_repository import ProjectRepository
from app.repository.run_repository import ProjectRunRepository
from app.repository.run_type_repository import RunTypeRepository
from app.repository.task_repository import TaskRepository
from app.helpers.path_helper import (
    create_project_run_input_path,
    create_dir_in_storage_path,
    create_task_input_path,
)


class CreateProjectRunUseCase:
    def __init__(
        self,
        session_factory: Callable[..., AbstractContextManager[Session]],
        project_repository: ProjectRepository,
        project_run_repository: ProjectRunRepository,
        run_type_repository: RunTypeRepository,
        task_repository: TaskRepository,
    ):
        self.session_factory = session_factory
        self.project_repository = project_repository
        self.project_run_repository = project_run_repository
        self.run_type_repository = run_type_repository
        self.task_repository = task_repository

    def create_project_run(self, project_run: ProjectRunInsert) -> ProjectRunDb:
        # Ensure proper transaction management with error handling
        with self.session_factory() as session:
            try:
                # Set session for all repositories
                self.project_repository.set_session(session)
                self.project_run_repository.set_session(session)
                self.run_type_repository.set_session(session)
                self.task_repository.set_session(session)

                result = self._create_project_run(project_run, session)

                # Commit at the end of the transaction
                session.commit()

                # Refresh after commit to get updated data
                session.refresh(result)

                logger.info(
                    f"Successfully created project run with ID: {result.id}"
                )
                return result

            except Exception as e:
                logger.exception("Error creating project run")
                session.rollback()
                raise

    def _create_project_run(
        self, project_run: ProjectRunInsert, session: Session
    ) -> ProjectRunDb:
        """
        1. create the run_project
        2. create the work area (on disk)
        3. create the tasks this run needs to execute
        4. add them to the task queue
        """
        try:
            self._validate_project_run(project_run)
            self._validate_project_run_attributes(project_run.attributes)

            # 1. create the run_project
            run_created: ProjectRunDb = self.project_run_repository.create(
                project_run
            )
            logger.info(f"Created project run: {run_created.id}")

            # 2. create the work area
            self.create_assign_project_paths(run_created)

            # 3. create the tasks
            run_type: RunType = self.run_type_repository.get_by_name(
                project_run.run_type
            )
            task_created_list = []
            sorted_tasks = sorted(run_type.tasks, key=lambda x: x.order)

            for task_t in sorted_tasks:
                # creating a task per model selected, unless the task does not depend on an interface
                interface_ids = (
                    run_created.attributes["interface_to_use"]
                    if task_t.is_interface_dependent
                    else [None]
                )

                for interface_id in interface_ids:
                    logger.info(
                        f"Creating task {task_t.name} for interface: {interface_id}"
                    )

                    # copy the dictionary run_created.attributes to avoid changing the original
                    altered_attributes = run_created.attributes.copy()
                    altered_attributes["interface_to_use"] = (
                        [interface_id] if interface_id is not None else []
                    )

                    task_to_insert = TaskInsert(
                        project_run_id=run_created.id,
                        task_type_id=task_t.id,
                        attributes=altered_attributes,
                        input_path=create_task_input_path(
                            run_created, task_t.name
                        ),
                        status=TaskStatusEnum.PENDING,
                        interface_id=interface_id,
                    )

                    task_added = self.task_repository.create(task_to_insert)
                    logger.info(f"Task created with ID: {task_added.id}")
                    task_created_list.append(task_added)

            # 4. Set first task status
            if task_created_list:
                first_task = task_created_list[0]
                first_task.status = TaskStatusEnum.PENDING
                logger.info(f"Set first task {first_task.id} to PENDING status")

            return run_created

        except Exception as e:
            logger.error(f"Error in _create_project_run: {str(e)}")
            raise

    def _validate_project_run(self, project_run: ProjectRunInsert) -> bool:
        try:
            project = self.project_repository.get_by_id(project_run.project_id)
            if project is None:
                raise ValueError("Project id does not exist")

            if not RunTypesEnum.has_member_key(project_run.run_type):
                raise ValueError("Run type does not exist")

            return True
        except Exception as e:
            logger.error(f"Error validating project run: {str(e)}")
            raise

    @staticmethod
    def create_assign_project_paths(project_run: ProjectRunDb) -> None:
        try:
            # First we need to create input paths per run
            input_path = create_project_run_input_path(project_run)
            create_dir_in_storage_path(input_path)
            project_run.input_path = input_path

            # Now we need to create output paths per run
            output_path = create_project_run_input_path(project_run)
            create_dir_in_storage_path(output_path)
            project_run.output_path = output_path

            logger.info(f"Created paths for project run {project_run.id}")
        except Exception as e:
            logger.error(f"Error creating project paths: {str(e)}")
            raise

    @staticmethod
    def _validate_project_run_attributes(attributes: dict[str, Any]) -> bool:
        if attributes is None or len(attributes) == 0:
            raise ValueError("Attributes are empty")

        # confidence level
        if "confidence_level" not in attributes:
            raise ValueError("The confidence level is missing")

        confidence_level = attributes["confidence_level"]
        if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
            raise ValueError("The confidence level must be a number")
        if confidence_level <= 0 or confidence_level > 100:
            raise ValueError("The confidence level must be between 0 and 100")

        # model ids
        if "interface_to_use" not in attributes:
            raise ValueError("The interface ids list is missing")

        interface_to_use = attributes["interface_to_use"]
        if not isinstance(interface_to_use, list) or len(interface_to_use) <= 0:
            raise ValueError("The interface ids list is empty")
        # One task is created per interface id, so the list is bounded and
        # duplicates are refused before any rows are written.
        max_interfaces = get_config().MAX_INTERFACES_PER_RUN
        if len(interface_to_use) > max_interfaces:
            raise ValueError(f"At most {max_interfaces} interfaces can be used per run")
        if any(isinstance(i, bool) or not isinstance(i, int) or i <= 0 for i in interface_to_use):
            raise ValueError("The interface ids must be positive integers")
        if len(set(interface_to_use)) != len(interface_to_use):
            raise ValueError("The interface ids list contains duplicates")

        # geojson bounding box
        if "bbox" not in attributes:
            raise ValueError("The bbox is missing")

        geojson_bounding_box = attributes["bbox"]
        if not isinstance(geojson_bounding_box, str) or len(geojson_bounding_box) == 0:
            raise ValueError("The geojson bounding box is empty")

        CreateProjectRunUseCase._validate_bounding_box(geojson_bounding_box)

        # the run's WMS url is what the tiler will fetch
        if "wms_server_url" in attributes:
            validate_wms_url(attributes["wms_server_url"])

        return True

    @staticmethod
    def _validate_bounding_box(bbox: str) -> bool:
        bounds = bbox.split(",")
        if len(bounds) != 4:
            raise ValueError("Bounding box is not valid")
        # bounds are: topLeft_x,topLeft_y,bottomRight_x,bottomRight_y
        # translated: min_x, max_y, max_x, min_y
        min_x = float(bounds[0])
        max_y = float(bounds[1])
        max_x = float(bounds[2])
        min_y = float(bounds[3])
        if min_x >= max_x or min_y >= max_y:
            raise ValueError(
                "Bounding box is not valid. The format should be: topLeft_x,topLeft_y,bottomRight_x,bottomRight_y"
            )

        return True
