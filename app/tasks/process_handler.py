from contextlib import AbstractContextManager
from datetime import datetime, timedelta
from typing import Callable
import os
import psutil
from sqlmodel import Session

from app.config import get_config
from app.db.models.task import TaskStatusEnum, TaskStepDb
from app.repository.task_step_repository import TaskStepRepository
import logging

logger = logging.getLogger()


class ProcessHandler:
    def __init__(
        self,
        session_factory: Callable[..., AbstractContextManager[Session]],
        task_step_repository: TaskStepRepository,
    ):
        self.task_step_repository = task_step_repository
        self.session_factory = session_factory
        self.pid: int = os.getpid()
        self.last_check_time: datetime = datetime.now()

        logger.info(f"ProcessHandler initialized with pid: {self.pid}")

    def kill_process(self, pid: int | None) -> bool:
        """Terminate a process this backend started. Returns True if signalled.

        The pid comes from the database, so it is never trusted on its own:
        missing, non-positive and own pids are refused (psutil.Process(None)
        would otherwise resolve to the backend itself), and only live
        descendants of this process may be terminated. A pid that survived a
        restart is no longer a child and is deliberately left alone, since the
        number may now belong to an unrelated process.
        """
        if pid is None or isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
            logger.warning(f"Refusing to kill invalid pid: {pid!r}")
            return False
        if pid == self.pid:
            logger.warning("Refusing to kill the backend's own process")
            return False

        try:
            own = psutil.Process(self.pid)
            if pid not in {c.pid for c in own.children(recursive=True)}:
                logger.warning(f"Refusing to kill pid {pid}: not a child of this backend")
                return False
            logger.info(f"Killing process with pid: {pid}")
            psutil.Process(pid).terminate()
            return True
        except psutil.NoSuchProcess:
            return False

    @staticmethod
    def _is_process_running(pid: int | None):
        if pid is None or pid <= 0 or not psutil.pid_exists(pid):
            return False
        process = psutil.Process(pid)
        return process.is_running()

    def _is_it_time_to_check(self):
        # Typically the dispatcher calls this every 5 seconds, but for now
        # we will check every 30 seconds instead
        if (datetime.now() - self.last_check_time).total_seconds() > 30:
            self.last_check_time = datetime.now()
            return True

        return False

    def check_for_long_running_steps(self):
        if not self._is_it_time_to_check():
            return

        with self.session_factory() as session:
            self.task_step_repository.set_session(session)

            timeout_seconds = get_config().TASK_STEP_TIMEOUT_SECONDS
            running_steps = self.task_step_repository.get_running_steps()

            for step in running_steps:
                # For each step that has been running for longer than x seconds,
                self.check_and_kill_long_running_process(step, timeout_seconds)

            session.commit()

    def check_and_kill_long_running_process(self, step: TaskStepDb,
                                            timeout_seconds:int):
        limit_time = datetime.now() - timedelta(seconds=timeout_seconds)

        if step.pid is None:
            # In-process step, or the subprocess has not been registered yet.
            # Start the clock if needed and only give up after the timeout.
            if step.started_at is None:
                step.started_at = datetime.now()
                return
            if step.started_at > limit_time:
                return
            step.status = TaskStatusEnum.ERROR
            return

        # check to see if the process is still running according to the system.
        if self._is_process_running(step.pid):
            # A missing started_at is stale state, not an exemption from the timeout.
            if step.started_at is not None and step.started_at > limit_time:
                running_time = (datetime.now() - step.started_at).total_seconds()
                # The process is still running and has not been running for longer
                # than the allowed time, so we can continue
                logger.info(
                    f"Process with pid: {step.pid} is still running according "
                    f"to system, total running time: {running_time}s"
                )
                return

            logger.info(
                f"Attempting to kill step {step.id} (with pid: {step.pid}) "
                f"because it has been running for longer than "
                f"{timeout_seconds} seconds"
            )
            # It is still running, attempt to kill it because it has been running
            # for longer than the allowed time
            self.kill_process(step.pid)

            # Since the process is still running, it has likely failed
            step.status = TaskStatusEnum.KILLED

            # Since the process is killed, we have no reason to keep the pid
            step.pid = None
        else:
            logger.info(
                f"Process with pid: {step.pid} is not running according to "
                f"system, cleaning up step {step.id}"
            )
            # The process is not running according to the system, but the backend
            # still believes it is running. We should set the pid to None
            # to indicate that the process is no longer running.
            step.pid = None

            step.status = TaskStatusEnum.ERROR

    def set_pid(self, task_step_id: int, pid: int):
        with self.session_factory() as session:
            self.task_step_repository.set_session(session)
            self.task_step_repository.set_pid(task_step_id, pid)
            session.commit()
