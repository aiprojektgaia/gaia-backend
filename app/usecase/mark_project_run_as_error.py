from contextlib import AbstractContextManager
from typing import Callable
from sqlmodel import Session

from app.db.models.task import TaskStatusEnum
from app.repository.task_repository import TaskRepository

from . import logger

class MarkProjectRunAsError:
    def __init__(
            self,
            session_factory: Callable[..., AbstractContextManager[Session]],
            task_repository: TaskRepository,
    ):
        self.session_factory = session_factory
        self.task_repository = task_repository


    def mark_project_run_as_error(self, project_run_id: int) -> int:
        with self.session_factory() as session:
            self.task_repository.set_session(session)
            result = self._mark_project_run_as_error(project_run_id)
            session.commit()
            return result


    def _mark_project_run_as_error(self, project_run_id: int) -> int:
        """
        1. get the run_project
        2. get its tasks
        3. for any project which has the status of QUEUED or RUNNING will be marked as KILLED
        """
        tasks = self.task_repository.get_by_run_id(project_run_id)

        counter = 0
        for task in tasks:
            if task.status == TaskStatusEnum.QUEUED or task.status == TaskStatusEnum.RUNNING:
                logger.debug(f"Marking task {task.id} as killed")
                task.status = TaskStatusEnum.KILLED
                counter += 1

        return counter