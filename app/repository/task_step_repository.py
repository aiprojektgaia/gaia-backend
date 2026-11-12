from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlmodel import col
from sqlalchemy import text

from app.db.models.task import (
    TaskStepDb,
    TaskStepInsert,
    TaskStepResultInsert,
    TaskStepResultDb,
    TaskStatusEnum,
)
from app.repository.base_repository import BaseRepository


class TaskStepRepository(BaseRepository):
    def get_all(self) -> list[TaskStepDb]:
        result = self.session.exec(select(TaskStepDb)).all()
        return list(result) if result else []

    def get_by_id(self, task_step_id: int) -> TaskStepDb | None:
        return self.session.get(TaskStepDb, task_step_id)

    def get_by_external_id(
        self, task_step_external_id: UUID
    ) -> TaskStepDb | None:
        statement = select(TaskStepDb).where(
            col(TaskStepDb.external_id) == task_step_external_id
        )
        # Note. If you don't add the scalars() method, the result will be a list of tuples
        return self.session.exec(statement).scalars().first()

    def get_by_task_id(self, task_id: int) -> list[TaskStepDb]:
        statement = select(TaskStepDb).where(col(TaskStepDb.task_id) == task_id)
        result = self.session.exec(statement).scalars().all()
        return list(result) if result else []

    # Swap meaning, QUEUED with PENDING, so this method makes sense
    def has_steps_pending(self, task_id: int) -> bool:
        statement = select(TaskStepDb).where(
            col(TaskStepDb.task_id) == task_id,
            col(TaskStepDb.status) == TaskStatusEnum.QUEUED,
        )
        return self.session.exec(statement).first() is not None

    def get_by_task_id_and_status(
        self, task_id: int, status: TaskStatusEnum
    ) -> list[TaskStepDb]:
        statement = select(TaskStepDb).where(
            col(TaskStepDb.task_id) == task_id,
            col(TaskStepDb.status) == status,
        )
        result = self.session.exec(statement).scalars().all()
        return list(result) if result else []

    def create(self, step: TaskStepInsert) -> TaskStepDb:
        db_step = TaskStepDb.model_validate(step)
        self.session.add(db_step)
        self.session.commit()
        self.session.refresh(db_step)
        return db_step

    def delete(self, task: TaskStepDb) -> None:
        self.session.delete(task)

    # step answer
    def save_answer(
        self, task_result: TaskStepResultInsert
    ) -> TaskStepResultDb:
        db_step_result = TaskStepResultDb.model_validate(task_result)
        self.session.add(db_step_result)
        return db_step_result

    def is_any_step_running(self):
        sql = text("""
    select count(1)
    from task t 
        inner join task_step ts on ts.task_id = t.id
    where t.status = 'RUNNING'
        and ts.status = t.status 
                   """)
        counter = self.session.execute(sql).scalar_one_or_none()
        return counter > 0

    def set_pid(self, task_step_id: int, pid: int) -> None:
        task_step = self.get_by_id(task_step_id)
        if task_step:
            task_step.pid = pid

    def get_running_steps(
        self, since_datetime: datetime = None
    ) -> list[TaskStepDb]:
        statement = select(TaskStepDb).where(
            col(TaskStepDb.status) == TaskStatusEnum.RUNNING,
        )
        if since_datetime is not None:
            statement = statement.where(
                TaskStepDb.started_at < since_datetime,
            )

        return self.session.exec(statement).scalars().all()

    def get_steps_running_longer_than(self, seconds: int) -> list[TaskStepDb]:
        cutoff_time = datetime.now() - timedelta(seconds=seconds)
        return self.get_running_steps(cutoff_time)
