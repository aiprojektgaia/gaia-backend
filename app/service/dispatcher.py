import importlib
import traceback
from contextlib import AbstractContextManager
from typing import Callable

from sqlmodel import Session

from app.db.models.task import TaskDb, TaskStatusEnum, TaskStepDb
from app.model.task_definition import TaskDefinition
from app.repository.task_repository import TaskRepository
from app.repository.task_step_repository import TaskStepRepository

from app.usecase.mark_project_run_as_error import MarkProjectRunAsError

import app.tasks.tasks as task_resolver

from . import logger


class Dispatcher:
    def __init__(
        self,
        session_factory: Callable[..., AbstractContextManager[Session]],
        task_repository: TaskRepository,
        task_step_repository: TaskStepRepository,
        mark_project_run_as_error_usecase: MarkProjectRunAsError,
    ):
        self.task_repository: TaskRepository = task_repository
        self.task_step_repository = task_step_repository
        self.mark_project_run_as_error_usecase = mark_project_run_as_error_usecase
        self.session_factory = session_factory

    def check_for_tasks(self) -> TaskDefinition | None:
        with self.session_factory() as session:
            self.task_repository.set_session(session)
            self.task_step_repository.set_session(session)
            return self._check_for_tasks(session)

    def _check_for_tasks(self, session: Session) -> TaskDefinition | None:
        logger.debug("Checking for tasks...")

        next_step = self.get_next_tasks(session)
        if next_step is None:
            logger.debug("No tasks found")
            return None

        session.commit()
        logger.debug(
            f"Found step with Id: {next_step.id} with taskType: {next_step} to run "
        )

        return TaskDefinition(
            task_type_name=next_step.task.task_type.name,
            task_step_id=next_step.id,
        )

    def get_next_tasks(self, session: Session) -> TaskStepDb | None:
        logger.debug(
            f"Has running tasks? : {self.task_repository.has_running_tasks()}"
        )
        if self.task_step_repository.is_any_step_running() is True:
            return None

        next_step = self.get_next_step_from_running_task()
        if next_step:
            return next_step

        next_task = self.pick_next_task_to_run()
        if next_task is None:
            return None

        try:
            next_step = self.create_steps_for_task(next_task, session)
            return next_step
        except Exception as e:
            logger.error(f"Error creating steps for taskId={next_task.id}: {e}")
            logger.error(traceback.format_exc())
            next_task.status = TaskStatusEnum.ERROR
            session.commit()
            affected_count = self.mark_project_run_as_error_usecase.mark_project_run_as_error(next_task.project_run_id)
            logger.info(f"Marked {affected_count} tasks as ERROR for project_run_id={next_task.project_run_id}")
            return None

    def get_next_step_from_running_task(self) -> TaskStepDb | None:
        tasks = self.task_repository.get_by_status(TaskStatusEnum.RUNNING)
        if len(tasks) > 0:
            running_task = tasks[0]
            steps = self.task_step_repository.get_by_task_id_and_status(
                running_task.id, TaskStatusEnum.QUEUED
            )
            if len(steps) > 0:
                return steps[0]

    def pick_next_task_to_run(self) -> TaskDb | None:
        tasks = self.task_repository.get_by_status(TaskStatusEnum.QUEUED)
        tasks.sort(key=lambda x: x.task_type.order)
        if len(tasks) > 0:
            return tasks[0]

        # time to find the next project_run to
        tasks = self.task_repository.get_by_status(TaskStatusEnum.PENDING)
        tasks.sort(key=lambda x: x.id)
        if len(tasks) == 0:
            return None

        same_project_tasks = [
            task
            for task in tasks
            if task.project_run_id == tasks[0].project_run_id
        ]
        for task in same_project_tasks:
            task.status = TaskStatusEnum.QUEUED

        return tasks[0]

    @staticmethod
    def create_steps_for_task(
        next_task: TaskDb, session: Session
    ) -> TaskStepDb:
        """
        The task has a name, from a task name, we can call the task_resolver to have a tailor made
        list of steps and checks to be run in order to do that step.
        """

        function_name = task_resolver.get_function_name_from_alias(next_task.task_type.name)
        logger.debug(f"Creating steps for task {next_task.task_type.name} ({function_name})")
        module = importlib.import_module(f"app.tasks.tasks.{function_name}")
        fn = getattr(module, function_name)
        if fn is None:
            raise Exception(
                f"Resolver-function for Task type {next_task.task_type.name} not found"
            )

        task_steps = fn(next_task, session)

        if len(task_steps) == 0:
            raise Exception(
                f"No steps found for Task type {next_task.task_type.name} ({next_task.id})"
            )

        next_task.status = TaskStatusEnum.RUNNING

        return task_steps[0]
