import os
import shutil
from contextlib import AbstractContextManager
from typing import Callable, List

from sqlmodel import Session

from . import logger

from app.db.models.task import TaskStepDb
from app.repository.project_repository import ProjectRepository
from app.repository.run_repository import ProjectRunRepository
from app.repository.run_type_repository import RunTypeRepository
from app.repository.task_repository import TaskRepository
from app.repository.task_step_repository import TaskStepRepository


class DeleteProjectRunUseCase:
    def __init__(
        self,
        session_factory: Callable[..., AbstractContextManager[Session]],
        project_repository: ProjectRepository,
        project_run_repository: ProjectRunRepository,
        run_type_repository: RunTypeRepository,
        task_repository: TaskRepository,
        task_step_repository: TaskStepRepository,
    ):
        self.session_factory = session_factory
        self.project_repository = project_repository
        self.project_run_repository = project_run_repository
        self.run_type_repository = run_type_repository
        self.task_repository = task_repository
        self.task_step_repository = task_step_repository

    """
        TODO: add one create method per run type.
        a run type will need to be associated to an interface group and the attributes property
        should include a list of models per group. If there is no group => should be reasonable to
        assume that all the models associated for that group will be run.
    """

    def delete_project_run(self, project_run_id: int) -> bool:
        with self.session_factory() as session:
            self.project_repository.set_session(session)
            self.project_run_repository.set_session(session)
            self.run_type_repository.set_session(session)
            self.task_repository.set_session(session)
            result = self._delete_project_run(project_run_id)
            session.commit()
            return result

    def _delete_project_run(self, project_run_id: int) -> bool:
        """
        1. get the run_project
        2. get its tasks
        3. get task steps
        4. per task step
            4.1 delete task step output data
            4.2 delete task step (including the result)
        5. delete the task output data
        6. delete the task
        7. delete the run_project
        """
        # 1. get the run_project
        project_run = self.project_run_repository.get_by_id(project_run_id)
        if project_run is None:
            raise ValueError("Project run id does not exist")

        # 2. get its tasks
        task_list = self.task_repository.get_by_run_id(project_run_id)

        # 3. get task steps
        for task in task_list:
            task_steps: List[TaskStepDb] = self.task_step_repository.get_by_task_id(task.id)

            # 4. per task step
            for task_step in task_steps:
                # 4.1 delete task step output data
                self.delete_folder_content(task_step.output_data_path)

                # 4.2 delete task step (including the result)
                self.task_step_repository.delete(task_step)

            # 5. delete the task output data
            self.delete_folder_content(task.output_path)

            # 6. delete the task
            self.task_repository.delete(task)

        # 7. delete the run_project
        self.delete_folder_content(project_run.output_path)
        self.project_run_repository.delete(project_run)

        return True

    @staticmethod
    def delete_folder_content(folder_path: str) -> bool:
        """
        This method will delete the content of the folder and the folder itself.
        """
        logger.info(f"Deleting folder content {folder_path}")

        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            logger.info(f"Deleted folder {folder_path}")
            return True
        else:
            logger.warning(f"Folder {folder_path} does not exist")
            return False
