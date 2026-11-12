from contextlib import AbstractContextManager
from typing import Callable, List

from sqlmodel import Session
from app.db.models.project import ProjectRunDb
from app.model.dto.project_run_public import ProjectRunPublic
from app.db.models.task import TaskStatusEnum

from app.repository.run_repository import ProjectRunRepository
from app.repository.task_repository import TaskRepository
from app.tasks.process_handler import ProcessHandler


class ProjectRunService:
    def __init__(
        self,
        session_factory: Callable[..., AbstractContextManager[Session]],
        project_run_repository: ProjectRunRepository,
        task_repository: TaskRepository,
        process_handler: ProcessHandler
    ):
        self.session_factory = session_factory
        self.project_run_repository = project_run_repository
        self.task_repository = task_repository
        self.process_handler = process_handler

    def get_project_runs(self, project_id: int) -> List[ProjectRunPublic]:
        with self.session_factory() as session:
            self.project_run_repository.set_session(session)
            project_runs = self.project_run_repository.get_by_project_id(project_id)

            public_runs: List[ProjectRunPublic] = []
            for project_run in project_runs:
                status_str = self.project_run_repository.get_status(project_run.id)
                public_run = ProjectRunPublic.from_project_run_db(project_run)
                public_run.status = status_str
                public_runs.append(public_run)
            return public_runs

    def get_project_run(self, run_id: int) -> ProjectRunDb:
        with self.session_factory() as session:
            self.project_run_repository.set_session(session)
            return self.project_run_repository.get_by_id(run_id)

    def delete_project_run(self, run_id: int) -> bool:
        # get project run by id
        # check that no tasks are running
        #   kill any running task
        # delete project run input folder
        # delete project run from db

        with self.session_factory() as session:
            self.project_run_repository.set_session(session)
            self.task_repository.set_session(session)

            project_run = self.project_run_repository.get_by_id(run_id)
            if project_run is None:
                raise ValueError("Project run does not exist")

            # check that no tasks are running
            self.kill_running_tasks(project_run)

            # delete project run input folder
            self._delete_project_run_files(project_run)

            # delete project run from db
            self._delete_project_run(project_run)

            session.commit()
            return True

    def kill_running_tasks(self, project_run: ProjectRunDb):
        # get all tasks for project run
        tasks = self.task_repository.get_by_run_id(project_run.id)
        # get all running tasks
        running_tasks = [t for t in tasks if t.status == TaskStatusEnum.RUNNING]

        # kill any running task
        for task in running_tasks:
            # get all running steps for task
            running_steps = [s for s in task.steps if s.status == TaskStatusEnum.RUNNING]

            for step in running_steps:
                # kill the process
                self.process_handler.kill_process(step.pid)

                # Since the process is still running, it has likely failed
                task.status = TaskStatusEnum.KILLED

                # Since the process is killed, we have no reason to keep the pid
                step.pid = None

            # not really needed but just in case
            task.status = TaskStatusEnum.KILLED

    def _delete_project_run(self, project_run: ProjectRunDb):
        print(f"Deleting run {project_run.id} -> {project_run}")
        self.project_run_repository.delete(project_run)

    def _delete_project_run_files(self, project_run: ProjectRunDb):
        path_to_delete = project_run.input_path
        # check if path exists
        import os
        if not os.path.exists(path_to_delete):
            print(f"Path {path_to_delete} does not exist, skipping deleting files")
            return

        import shutil
        shutil.rmtree(path_to_delete, onerror=self._on_file_delete_error)

    @staticmethod
    def _on_file_delete_error(function, path, excinfo):
        print(f"Error deleting file: {path}. Function is {function}. Error is {excinfo}")
