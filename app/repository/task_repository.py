from typing import List
import logging

from sqlalchemy import Sequence, text
from sqlmodel import select, delete

from app.db.models.task import TaskDb, TaskInsert, TaskStatusEnum
from app.repository.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class TaskRepository(BaseRepository):
    def get_all(self) -> Sequence[TaskDb]:
        try:
            return self.session.exec(select(TaskDb)).all()
        except Exception as e:
            logger.error(f"Error in get_all: {str(e)}")
            raise

    def get_by_id(self, task_id: int) -> TaskDb | None:
        try:
            return self.session.get(TaskDb, task_id)
        except Exception as e:
            logger.error(f"Error in get_by_id({task_id}): {str(e)}")
            raise

    def has_running_tasks(self) -> bool:
        try:
            statement = select(
                select(TaskDb)
                .where(TaskDb.status == TaskStatusEnum.RUNNING)
                .exists()
            )
            result = self.session.exec(statement)
            return result.first() or False
        except Exception as e:
            logger.error(f"Error in has_running_tasks: {str(e)}")
            raise

    def get_by_status(self, status: TaskStatusEnum) -> list[TaskDb]:
        try:
            statement = (
                select(TaskDb)
                .where(TaskDb.status == status)
                .order_by(TaskDb.project_run_id)
                .order_by(TaskDb.task_type_id)
            )
            return self.session.exec(statement).all()
        except Exception as e:
            logger.error(f"Error in get_by_status({status}): {str(e)}")
            raise

    def get_by_run_id(self, run_id: int) -> List[TaskDb]:
        try:
            statement = select(TaskDb).where(TaskDb.project_run_id == run_id)
            return self.session.exec(statement).all()
        except Exception as e:
            logger.error(f"Error in get_by_run_id({run_id}): {str(e)}")
            raise

    def create(self, task_insert: TaskInsert) -> TaskDb:
        try:
            db_task = TaskDb.model_validate(task_insert)
            self.session.add(db_task)
            self.session.flush()  # Use flush to get the ID without committing
            return db_task
        except Exception as e:
            logger.error(f"Error in create: {str(e)}")
            self.safe_rollback()
            raise

    def delete(self, task: TaskDb) -> None:
        try:
            self.session.delete(task)
            # Don't commit here - let the use case handle transactions
        except Exception as e:
            logger.error(f"Error in delete: {str(e)}")
            self.safe_rollback()
            raise

    def delete_project(self, project_run_id: int) -> None:
        try:
            result = self.session.exec(
                delete(TaskDb).where(TaskDb.project_run_id == project_run_id)
            )
            logger.info(
                f"Deleted tasks for project_run_id {project_run_id}, count: {result.rowcount}"
            )
        except Exception as e:
            logger.error(f"Error in delete_project({project_run_id}): {str(e)}")
            self.safe_rollback()
            raise

    def get_total_finished_subtasks(self, project_run_id: int) -> int:
        try:
            # Use parameterized query to prevent SQL injection
            sql = text("""
                SELECT COUNT(1)
                FROM task_step ts 
                    INNER JOIN task t ON ts.task_id = t.id
                WHERE ts.status = 'FINISHED'
                    AND t.project_run_id = :project_run_id
            """)
            counter = self.session.execute(
                sql, {"project_run_id": project_run_id}
            ).scalar_one_or_none()
            return counter or 0
        except Exception as e:
            logger.error(
                f"Error in get_total_finished_subtasks({project_run_id}): {str(e)}"
            )
            raise
