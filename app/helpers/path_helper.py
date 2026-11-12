import datetime
import os
import random
import string

from pathlib import Path

from app.config import get_config

from app.db.models.project import ProjectRunDb
from app.db.models.task import TaskStepDb

"""
    project_run is: 'project-{project_id}/run-{run_id}'
"""


def create_project_run_input_path(project_run: ProjectRunDb) -> str:
    # input_path = os.path.join(f"project-{project_run.project_id}", f"run-{project_run.id}")
    project_path = (
        Path(get_config().STORAGE_PATH) / f"project-{project_run.project_id}"
    )
    project_path.exists() or project_path.mkdir()

    run_path = project_path / f"run-{project_run.id}"
    run_path.exists() or run_path.mkdir()

    return str(run_path)


"""
    project_run is: 'project-{project_id}/run-{run_id}/output'
"""


def create_project_run_output_path(project_run: ProjectRunDb) -> str:
    # input_path = os.path.join(f"project-{project_run.project_id}", f"run-{project_run.id}", "output")
    run_path = Path(create_project_run_input_path(project_run))
    output_path = run_path / "output"
    os.makedirs(output_path, exist_ok=True)

    return str(output_path)


"""
    project_run is: 'project-{project_id}/run-{run_id}/{task_type_name}'
"""


def create_task_input_path(
    project_run: ProjectRunDb, task_type_name: str
) -> str:
    # input_path = os.path.join(project_run.input_path, task_type_name)
    input_path = Path(project_run.input_path) / task_type_name
    os.makedirs(input_path, exist_ok=True)

    return str(input_path)


"""
    project_run is: 'project-{project_id}/run-{run_id}/{task_type_name}/{task_step_id}'
"""


def create_task_step_input_path(task_step: TaskStepDb) -> str:
    # input_path = os.path.join(task_step.input_path, f"{task_step.id}")
    input_path = Path(task_step.input_path) / f"{task_step.id}"
    os.makedirs(input_path, exist_ok=True)

    return str(input_path)


"""
    project_run is: 'project-{project_id}/run-{run_id}/{task_type_name}/{task_step_id}/output'
"""


def create_task_step_output_path(task_step: TaskStepDb) -> str:
    output_path = Path(task_step.input_path) / "output"
    os.makedirs(output_path, exist_ok=True)

    return str(output_path)

def create_output_path(input_path: str) -> str:
    output_path = Path(input_path) / "output"
    os.makedirs(output_path, exist_ok=True)

    return str(output_path)

"""
    project_run is: 'project-{project_id}/run-{run_id}/{task_type_name}/{task_step_id}/{file_path}'
"""


def get_task_step_input_path_to_file(
    task_step: TaskStepDb, file_path: str
) -> str:
    input_path = os.path.join(
        task_step.input_path, f"{task_step.id}", file_path
    )

    return input_path


def create_extra_folder_for_interface(path: str, interface_id: int) -> str:
    # return os.path.join(path, extra_folder)
    extra_path = Path(path) / f"interface_{interface_id}"
    os.makedirs(extra_path, exist_ok=True)

    return str(extra_path)


def create_extra_folder_to_path(path: str, extra_folder: str) -> str:
    # return os.path.join(path, extra_folder)
    extra_path = Path(path) / extra_folder
    os.makedirs(extra_path, exist_ok=True)

    return str(extra_path)


def merge_path_with_extra_folder(path: str, extra_folder: str) -> str:
    return os.path.join(path, extra_folder)


def get_absolute_path(path: str) -> str:
    config = get_config()
    storage_path = config.STORAGE_PATH

    return os.path.join(storage_path, path)


def create_dir_in_storage_path(path: str) -> None:
    absolute_path = get_absolute_path(path)
    os.makedirs(absolute_path, exist_ok=True)


def get_files_from_path_orig(path: str) -> list[str]:
    absolute_path = get_absolute_path(path)
    files = [
        f
        for f in os.listdir(absolute_path)
        if os.path.isfile(os.path.join(absolute_path, f))
    ]

    return files


def get_files_from_path(path: str) -> list[str]:
    files = [
        f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))
    ]

    return files


def get_files_from_path_with_extension(path: str, extension: str) -> list[str]:
    absolute_path = get_absolute_path(path)
    files = [f for f in os.listdir(absolute_path) if f.endswith(extension)]

    return files


def navigate_to_parent_folder(path: str, num_jumps_back: int = 1) -> str:
    current_path = Path(path)
    for _ in range(num_jumps_back):
        current_path = current_path.parent
    return str(current_path)


def get_files_recursively_with_extension(
    path: str, extensions: list[str]
) -> list[str]:
    absolute_path = get_absolute_path(path)
    files = []

    for root, _, filenames in os.walk(absolute_path):
        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                # Get absolute path by joining root and filename
                full_path = os.path.join(root, filename)
                files.append(full_path)

    return files


def validate_path_access(path: str) -> tuple[bool, str]:
    temp_filename = f'system_verification_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.tmp'
    test_content = "".join(random.choices(string.ascii_letters, k=16))
    full_path = os.path.join(path, temp_filename)

    try:
        if not os.path.exists(path):
            return False, f"Path does not exist: {path}"

        # Write test file
        with open(full_path, "w") as f:
            f.write(test_content)

        # Read and verify content
        with open(full_path, "r") as f:
            read_content = f.read()

        if read_content != test_content:
            return False, "Content of test file does not match"

        return (
            True,
            "Write, read and delete filesystem access validated successfully",
        )

    except Exception as e:
        return False, str(e)

    finally:
        # Clean up - attempt to remove temp file
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
        except Exception:
            pass
