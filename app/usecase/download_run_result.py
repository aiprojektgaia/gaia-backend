from contextlib import AbstractContextManager
from typing import Callable
import zipfile
import os
import shutil
import tempfile
import threading
from typing import BinaryIO

from sqlmodel import Session
from app.db.models.project import ProjectRunDb
from app.db.models.task import TaskStatusEnum
from app.config import get_config
from app.helpers.path_helper import get_files_recursively_with_extension
from app.repository.run_repository import ProjectRunRepository
from app.repository.task_repository import TaskRepository
from app.repository.task_step_repository import TaskStepRepository


_download_slots: threading.BoundedSemaphore | None = None
_download_slots_lock = threading.Lock()


def _slots() -> threading.BoundedSemaphore:
    # Created on first use, not at import: the config is not loaded yet when
    # the container imports this module.
    global _download_slots
    with _download_slots_lock:
        if _download_slots is None:
            _download_slots = threading.BoundedSemaphore(get_config().DOWNLOAD_MAX_CONCURRENT)
        return _download_slots


class _SlotHeldArchive:
    """The temporary archive plus the download slot it occupies. The slot is
    released only when the archive is closed (after streaming finishes or the
    client goes away), so slow downloads still count against the limit and
    temporary disk use stays below DOWNLOAD_MAX_CONCURRENT x DOWNLOAD_MAX_BYTES."""

    def __init__(self, file):
        self._file = file
        self._released = False

    def read(self, size: int = -1) -> bytes:
        return self._file.read(size)

    def close(self) -> None:
        try:
            self._file.close()
        finally:
            if not self._released:
                self._released = True
                _slots().release()

    def __del__(self):
        self.close()


class DownloadRunResultUseCase:
    def __init__(
        self,
        session_factory: Callable[..., AbstractContextManager[Session]],
        project_run_repository: ProjectRunRepository,
        task_repository: TaskRepository,
        task_step_repository: TaskStepRepository,
    ) -> None:
        self.session_factory = session_factory
        self.project_run_repository = project_run_repository
        self.task_repository = task_repository
        self.task_step_repository = task_step_repository

    def handle(self, project_run_case_id: int) -> BinaryIO:
        with self.session_factory() as session:
            self.project_run_repository.set_session(session)
            self.task_repository.set_session(session)
            self.task_step_repository.set_session(session)
            result = self._handle(project_run_case_id)
            return result

    def validate_project_run_is_downloadable(
        self, project_run_case_id: int
    ) -> bool:
        tasks = self.task_repository.get_by_run_id(project_run_case_id)
        # Only a run that has stopped may be downloaded: nothing pending,
        # queued or running (results are still being written otherwise).
        active = {TaskStatusEnum.PENDING, TaskStatusEnum.QUEUED, TaskStatusEnum.RUNNING}
        return bool(tasks) and not any(task.status in active for task in tasks)

    def _handle(self, project_run_case_id: int) -> BinaryIO:
        project_run: ProjectRunDb | None = (
            self.project_run_repository.get_by_id(project_run_case_id)
        )
        if project_run is None:
            raise ValueError(
                f"Project run with id {project_run_case_id} not found"
            )

        if not self.validate_project_run_is_downloadable(project_run_case_id):
            raise ValueError(
                f"Project run with id {project_run_case_id} has not finished yet"
            )

        files = get_files_recursively_with_extension(
            project_run.input_path, [".gpkg", ".tif"]
        )

        if len(files) == 0:
            raise ValueError(
                f"No files found for project run with id {project_run_case_id}"
            )

        config = get_config()
        if len(files) > config.DOWNLOAD_MAX_FILES:
            raise ValueError("The run has too many result files to download")
        # lstat so a symlink cannot smuggle in a file from elsewhere
        sizes = []
        for file_path in files:
            st = os.lstat(file_path)
            if not os.path.isfile(file_path) or os.path.islink(file_path):
                raise ValueError("Unexpected non-regular file in the run results")
            sizes.append(st.st_size)
        if sum(sizes) > config.DOWNLOAD_MAX_BYTES:
            raise ValueError("The run results are too large to download")

        if shutil.disk_usage(tempfile.gettempdir()).free < sum(sizes) * 1.1 + 1024**3:
            raise ValueError("Not enough temporary disk space to build the archive")

        if not _slots().acquire(blocking=False):
            raise ValueError("Too many downloads in progress, try again later")
        # Build the archive in a temporary file on disk, not in memory. The
        # file is removed, and the slot released, when the caller closes it.
        archive = _SlotHeldArchive(tempfile.TemporaryFile(suffix=".zip"))
        try:
            with zipfile.ZipFile(archive._file, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
                for file_path in files:
                    zipf.write(file_path, os.path.basename(file_path))
            archive._file.seek(0)
        except BaseException:
            archive.close()
            raise
        return archive
