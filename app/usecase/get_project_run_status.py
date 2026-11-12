from app.db.models.task import TaskDb, TaskStatusEnum
from app.repository.run_repository import ProjectRunRepository
from app.repository.task_repository import TaskRepository

from contextlib import AbstractContextManager
from typing import Callable, List

from . import logger

from sqlmodel import Session

from app.model.project_run_status import ProjectRunStatus


class GetProjectRunStatusUseCase:
    def __init__(
        self,
        session_factory: Callable[..., AbstractContextManager[Session]],
        project_run_repository: ProjectRunRepository,
        task_repository: TaskRepository,
    ):
        self.session_factory = session_factory
        self.project_run_repository = project_run_repository
        self.task_repository = task_repository

    def get_project_run_status(self, run_id: int) -> ProjectRunStatus:
        with self.session_factory() as session:
            self.project_run_repository.set_session(session)
            self.task_repository.set_session(session)

        return self._get_project_run_status(run_id)

    @staticmethod
    def _get_total_finished_tasks(tasks: List[TaskDb]) -> int:
        # A project run with any failed or killed task should be considered incomplete
        # and only return 0 remaining tasks (since they will not be retried)
        if any(
            t.status in [TaskStatusEnum.KILLED, TaskStatusEnum.ERROR]
            for t in tasks
        ):
            return 0

        # All other tasks are considered remaining as long as they are not finished
        return len([t for t in tasks if t.status == TaskStatusEnum.FINISHED])

    def _get_project_run_status(self, run_id: int) -> ProjectRunStatus:
        run = self.project_run_repository.get_by_id(run_id)
        if run is None:
            raise ValueError("Could not find run with id: " + str(run_id))

        # Get the tasks for the run
        tasks = self.task_repository.get_by_run_id(run_id)
        if tasks is None:
            raise ValueError(
                "Could not find tasks for run with id: " + str(run_id)
            )

        # Check for statuses in order of priority, which means that the returned status
        # of the call will be the first found in the list of tasks, according to this priority.
        status_checks = [
            (
                TaskStatusEnum.KILLED,
                "Project tasks has timed out",
            ),
            (TaskStatusEnum.ERROR, "Project tasks has errors"),
            (TaskStatusEnum.PENDING, "Project run is waiting to be processed"),
            (TaskStatusEnum.RUNNING, "Project tasks are processing"),
            (TaskStatusEnum.QUEUED, "Project tasks are queued"),
            (TaskStatusEnum.FINISHED, "Project run has finished"),
        ]

        for status, message in status_checks:
            if any(t.status == status for t in tasks):
                return self.get_detailed_status(tasks, status, message)

        return ProjectRunStatus(
            message=f"Could not identify the status for run with id: {run_id}",
            status=TaskStatusEnum.PENDING,
            finished_tasks=self._get_total_finished_tasks(tasks),
            total_tasks=len(tasks),
        )

    def get_detailed_status(self, tasks: list[TaskDb], status, message):
        running_task: TaskDb = next(
            (t for t in tasks if t.status == TaskStatusEnum.RUNNING), tasks[-1]
        )

        calculated_total_steps = self.calculate_total_steps(tasks)
        total_finished_tasks = self._get_total_finished_tasks(tasks)
        total_finished_steps = self.task_repository.get_total_finished_subtasks(
            running_task.project_run_id
        )
        return ProjectRunStatus(
            calculating=total_finished_tasks == 0,
            message=message,
            status=status,
            finished_tasks=total_finished_tasks,
            total_tasks=len(tasks),
            current_task_name=running_task.task_type.name,
            total_finished_step=total_finished_steps,
            total_steps=calculated_total_steps,
        )

    @staticmethod
    def calculate_total_steps(tasks: list[TaskDb]) -> int:
        total_tasks = len(tasks)

        # get the task with no interface
        wms_task = next((t for t in tasks if t.interface_id is None), None)
        if wms_task is None:
            logger.warning("The tiler task doesn't exist, what?")
            return total_tasks
        elif wms_task.status != TaskStatusEnum.FINISHED:
            logger.debug("The tiler task is currently running.")
            return total_tasks

        # get the first step of the task (it only has one step)
        if len(wms_task.steps) == 0:
            logger.warning("The tiler task has no steps. This is bad."
            )
            return total_tasks

        step = wms_task.steps[0]
        step_result = next((t for t in step.result if t.success), None)
        if step_result is None:
            logger.debug("The tiler task was not successful.")
            return total_tasks

        total_tiles_created = step_result.additional_info.get(
            "total_tiles_expected", 0
        )

        if total_tiles_created == 0:
            logger.debug(
                f"could not get the total tiles created from the result: {step_result.additional_info}"
            )
            return total_tasks

        # how many segmentation tasks do we have?
        segmentation_tasks = [
            t for t in tasks if t.task_type.name == "SegmentProcess"
        ]
        total_segmentation_tasks = len(segmentation_tasks)

        total_steps = (
            len(tasks)
            - total_segmentation_tasks
            + (total_segmentation_tasks * total_tiles_created)
        )
        logger.debug(
            f"total steps:{total_steps}, total segmentation tasks: {total_segmentation_tasks}, total tiles created: {total_tiles_created}"
        )

        return total_steps
