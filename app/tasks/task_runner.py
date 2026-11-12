import asyncio
import logging
import sys
import os
from typing import Any
from app.config import get_config
from app.container import Container
from app.db.models.interface_group import InterfaceDb
import traceback

from app.db.models.task import TaskStatusEnum


logger = logging.getLogger()


async def execute_model(
    interface: InterfaceDb, task_step_id: int, additional_arguments: dict = None
) -> None:
    """
    This method is used to run a command in a separate subprocess
    and to handle any errors that may occur. This method is fire-and-forgotten
    and should not return any values. If it needs to report errors, it should
    do this via the database or the logger.
    """
    try:
        logger.info(
            f"Calling AI engine with function: {interface.function_name}"
        )

        ai_engine_path = os.path.join(
            get_config().MODEL_BASE_PATH, interface.path
        )
        command = prepare_command(
            interface, ai_engine_path, additional_arguments
        )
        asyncio.create_task(
            execute_command(command, task_step_id, ai_engine_path)
        )

    except Exception as e:
        logger.error(f"Unexpected error in prepare_engine_task: {str(e)}")
        logger.error(traceback.format_exc())
        raise ValueError(f"Unexpected error: {str(e)}")


def prepare_command(
    interface: InterfaceDb,
    ai_engine_path: str,
    additional_arguments: dict = None,
) -> list[str]:
    # Validate that the interface is installed
    if not interface.installed:
        raise ValueError(
            "Interface is not installed. Please install the interface before calling the AI engine."
        )

    if not interface.is_active:
        raise ValueError(
            "Interface is not active. Please activate the interface before calling the AI engine."
        )

    venv_path = interface.venv_path
    # Check if the path resolves
    full_path = os.path.join(ai_engine_path, interface.module_file_name)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Path {full_path} does not exist")

    # Construct the command to run the script
    if sys.platform.startswith("win"):
        python_executable = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        python_executable = os.path.join(venv_path, "bin", "python")

    command = [python_executable, interface.module_file_name]
    command.extend(build_command_args(interface.args))
    if additional_arguments:
        command.extend(build_command_args(additional_arguments))

    return command


async def execute_command(
    command: list[str],
    task_step_id: int,
    working_dir: str | None = None,
) -> None:
    process_handler = Container.process_handler()
    logger.debug(f"Command: {command}")

    # Run the command as a subprocess asynchronously
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=working_dir,  # Set the working directory for the subprocess
    )

    pid = process.pid
    if pid is not None:
        logger.info(
            f"Command started with pid: {pid} for task step id: {task_step_id}"
        )
        process_handler.set_pid(task_step_id, pid)
    else:
        logger.error(f"Did not receive a pid for task step id: {task_step_id}")

    # Intentionally set timeout to None, because we have other mechanisms to
    # handle long running processes
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=None)

    if process.returncode == 0:
        # Regardless if the command completes, we are not responsible for finishing
        # the task step. This is handled by the interface using a callback.
        logger.info("Command completed successfully")
        pass
    else:
        # TODO: if this is killed by the ProcessHandler, the ProcessHandler updates the task step
        # accordingly, but that is only one of the (controlled) ways a process can end
        logger.warning(
            f"Command failed with return code: {process.returncode}, stdout: {stdout}, stderr: {stderr}"
        )
        pass


def build_default_args(**kwargs) -> dict[str, Any]:
    return {key: str(value) for key, value in kwargs.items()}


def build_command_args(args: dict, formatters: dict = None) -> list[str]:
    """
    Builds CLI-like arguments from a dictionary.
    Allows custom formatting for specific argument types through the formatters dict.

    Args:
        base_command: The initial command
        args: Dictionary of arguments to convert to CLI format
        formatters: Optional dict of key -> formatter functions to customize argument formatting

    Example formatters:
        {"output_path": lambda x: f"--output_path={x}"}

    """
    command = []
    formatters = formatters or {}

    for key, value in args.items():
        key = key.replace("_", "-")

        # Skip None values
        if value is None:
            continue

        # Apply custom formatter if one exists for this key
        if key in formatters:
            value = formatters[key](value)
        elif isinstance(value, list):
            value = ",".join(map(str, value))
        else:
            value = str(value)

        command.append(f"--{key}={value}")

    return command


def set_task_step_as_failed(task_step_id: int):
    session_factory = Container.session_factory()
    task_step_repository = Container.task_step_repository()
    with session_factory() as session:
        task_step_repository.set_session(session)
        task_step = task_step_repository.get_by_id(task_step_id)
        task_step.status = TaskStatusEnum.ERROR
        session.expire_on_commit = False
        session.commit()
