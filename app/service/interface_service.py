import logging
import json
import os
import subprocess
import sys
import venv
from contextlib import AbstractContextManager
from typing import Any, Callable, List

from pydantic import BaseModel, Field
from sqlmodel import Session

from app.system_state import system_state
from app.config import get_config
from app.db.models.interface_group import InterfaceDb, InterfaceInsert
from app.repository.interface_repository import InterfaceRepository

logger = logging.getLogger()

excluded_folders = {
    # Version Control
    ".git",
    ".svn",
    ".hg",
    # Python-specific
    "__pycache__",
    "venv",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".coverage",
    # IDE-specific
    ".idea",
    ".vscode",
    ".vs",
    # macOS
    ".DS_Store",
    "__MACOSX",
}


class InterfaceDefinition(BaseModel):
    name: str
    group: str
    description: str
    args: dict[str, Any] = Field(default_factory=dict)
    function_name: str
    module_file_name: str


class ScannedInterface(BaseModel):
    path: str
    name: str
    has_requirements: bool
    has_main_file: bool
    definition: InterfaceDefinition


class InterfaceService:
    def __init__(
        self,
        session_factory: Callable[..., AbstractContextManager[Session]],
        interface_repository: InterfaceRepository,
    ):
        self.interface_repository: InterfaceRepository = interface_repository
        self.session_factory = session_factory

    def scan_and_install_interfaces(self):
        base_path = get_config().MODEL_BASE_PATH
        filesystem_interfaces = scan_interfaces(base_path)

        if len(filesystem_interfaces) == 0:
            logger.info("No interfaces found to install")
            return

        with self.session_factory() as session:
            self.interface_repository.set_session(session)
            installed_interfaces = self.interface_repository.get_all()

        for filesystem_interface in filesystem_interfaces:
            matching_interface = next(
                (
                    i
                    for i in installed_interfaces
                    if i.name.lower() == filesystem_interface.name.lower()
                ),
                None,
            )

            # We have the interface in both filesystem and database, make sure it's active/installed
            if matching_interface is not None:
                self.install_existing_interface(
                    matching_interface, filesystem_interface.path
                )

            # We don't have the interface in the database, but in filesystem.
            if matching_interface is None:
                self.add_new_interface(filesystem_interface)

        self.find_non_working_interfaces(
            installed_interfaces, filesystem_interfaces
        )

        logger.info("Finished scanning and installing interfaces")
        system_state.set_interfaces_installed()

    def install_existing_interface(
        self, matching_interface: InterfaceDb, filesystem_path: str
    ):
        # We have the interface in both filesystem and database, make sure it's active/installed
        try:
            # TODO: We should also update the interface in the database with properties
            # TODO: like description, args, etc. But these should be read from "some" file in the model folder
            venv_path = setup_ai_engine_environment(filesystem_path)
            with self.session_factory() as session:
                self.interface_repository.set_session(session)
                result = self.interface_repository.install_interface(
                    matching_interface.id, filesystem_path, venv_path
                )
                if not result:
                    logger.error(
                        f"Error installing interface (could not find it) {matching_interface.name}"
                    )
        except Exception as e:
            logger.error(
                f"Error setting up interface {matching_interface.name}: {e}"
            )
            with self.session_factory() as session:
                self.interface_repository.set_session(session)
                result = self.interface_repository.uninstall_interface(
                    matching_interface.id
                )
            if not result:
                logger.error(
                    f"Error uninstalling interface (could not find it) {matching_interface.name}"
                )

    def add_new_interface(self, interface: ScannedInterface):
        if not interface.has_requirements:
            logger.warning(
                f"Interface {interface.name} does not have a requirements.txt file, will not install"
            )
            return

        if not interface.has_main_file:
            logger.warning(
                f"Interface {interface.name} does not have a main.py file, will not install"
            )
            return

        try:
            venv_path = setup_ai_engine_environment(interface.path)
        except Exception as e:
            logger.error(f"Error setting up interface {interface.name}: {e}")
            return

        with self.session_factory() as session:
            self.interface_repository.set_session(session)

            segmentation_group = self.interface_repository.get_group_by_name(
                interface.definition.group
            )

            if segmentation_group is None:
                logger.error(
                    f"Interface {interface.name} does not have a valid group, please double-check the model.json file at {interface.path}"
                )
                return

            new_interface = InterfaceInsert(
                name=interface.name,
                interface_group_id=segmentation_group.id,
                path=interface.path,
                module_file_name=interface.definition.module_file_name,
                function_name=interface.definition.function_name,
                description=interface.definition.description,
                args=interface.definition.args,
                venv_path=venv_path,
                installed=True,
                is_active=True,
            )

            self.interface_repository.add(new_interface)
            session.commit()

    def find_non_working_interfaces(
        self,
        installed_interfaces: List[InterfaceDb],
        filesystem_interfaces: List[ScannedInterface],
    ):
        # Get the interfaces that are in installed_interfaces but not in filesystem_interfaces by path
        # and uninstall them
        for interface in installed_interfaces:
            if interface.path not in [f.path for f in filesystem_interfaces]:
                self.uninstall_interface(interface)

    def uninstall_interface(self, interface: InterfaceDb):
        with self.session_factory() as session:
            self.interface_repository.set_session(session)
            self.interface_repository.uninstall_interface(interface.id)
            session.commit()

    def get_interface_by_name(self, name: str) -> InterfaceDb | None:
        with self.session_factory() as session:
            self.interface_repository.set_session(session)
            return self.interface_repository.get_by_name(name)

    def get_interface_by_id(self, id: int) -> InterfaceDb | None:
        with self.session_factory() as session:
            self.interface_repository.set_session(session)
            return self.interface_repository.get(id)

    def get_installed_interfaces(self) -> List[InterfaceDb]:
        with self.session_factory() as session:
            self.interface_repository.set_session(session)
            return self.interface_repository.get_all_installed()

    def get_all_interfaces(self) -> List[InterfaceDb]:
        with self.session_factory() as session:
            self.interface_repository.set_session(session)
            return self.interface_repository.get_all_eager()

    @staticmethod
    def is_interface_runnable(interface: InterfaceDb):
        base_path = get_config().MODEL_BASE_PATH
        if not interface.is_active or not interface.installed:
            raise ValueError(
                f"Interface {interface.name} is not active or installed"
            )

        if not os.path.exists(interface.path):
            raise FileNotFoundError(
                f"Interface {interface.name} not found in filesystem ({os.path.join(base_path, interface.path)})"
            )

        if not os.path.exists(interface.venv_path):
            raise FileNotFoundError(
                f"Virtual environment for interface {interface.name} not found in filesystem ({interface.venv_path})"
            )

        if not os.path.exists(
            os.path.join(base_path, interface.path, interface.module_file_name)
        ):
            raise FileNotFoundError(
                f"Main file for interface {interface.name} not found in filesystem ({os.path.join(base_path, interface.path, interface.module_file_name)})"
            )

        return True


def scan_interfaces(base_path: str, depth=1) -> List[ScannedInterface]:
    """
    Scan the interfaces in the given base path.
    The depth parameter is the maximum depth of the subdirectories to scan.
    The initial base-path is considered depth 0
    """
    if not os.path.exists(base_path):
        raise FileNotFoundError(f"Base path {base_path} does not exist")

    if not os.access(base_path, os.R_OK):
        raise PermissionError(f"No read access to base path {base_path}")

    interfaces: List[ScannedInterface] = []

    def scan_directory(current_path: str, current_depth: int):
        if current_depth > depth:
            return

        for item in os.listdir(current_path):
            # Skip excluded folders
            if item in excluded_folders:
                continue

            item_path = os.path.join(current_path, item)
            if os.path.isdir(item_path):
                has_requirements = os.path.exists(
                    os.path.join(item_path, "requirements.txt")
                )
                has_main_file = os.path.exists(
                    os.path.join(item_path, "main.py")
                )
                definition = try_get_interface_definition(item_path)
                # If we have a definition, stop scanning this directory and add the definition
                if definition is None:
                    # If we don't have a definition inside this directory, search the subdirectories
                    scan_directory(item_path, current_depth + 1)
                    continue

                for def_item in definition:
                    interfaces.append(
                        ScannedInterface(
                            path=item_path,
                            name=def_item.name,
                            has_requirements=has_requirements,
                            has_main_file=has_main_file,
                            definition=def_item,
                        )
                    )

    # Start scanning from the base path
    scan_directory(base_path, 0)

    return interfaces


def create_venv_if_not_exists(venv_path: str) -> bool:
    if not os.path.exists(venv_path):
        logger.info(f"Creating virtual environment at {venv_path}")
        venv.create(venv_path, with_pip=True)
        return True
    return False


def install_requirements(
    venv_path: str, requirements_file: str, created_venv: bool
):
    if sys.platform.startswith("win"):
        pip_path = os.path.join(venv_path, "Scripts", "pip.exe")
    else:
        pip_path = os.path.join(venv_path, "bin", "pip")

    msg = " for the first time, this may take a while" if created_venv else ""
    logger.info(f"Installing requirements from {requirements_file}{msg}")

    # No check=True here: it raises CalledProcessError before we can read the
    # captured output, which reduces the caller's log line to "returned
    # non-zero exit status 1" and discards the reason the install failed.
    result = subprocess.run(
        [pip_path, "install", "-r", requirements_file],
        capture_output=True,
    )
    if result.returncode != 0:
        # Build failures land on stderr, but some resolver errors only appear
        # on stdout - report whichever is populated.
        details = (
            result.stderr.decode("utf-8", errors="replace").strip()
            or result.stdout.decode("utf-8", errors="replace").strip()
            or f"pip exited with status {result.returncode}"
        )
        raise Exception(
            f"Error installing requirements from {requirements_file}: {details}"
        )


def setup_ai_engine_environment(ai_engine_path: str) -> str:
    venv_path = os.path.join(ai_engine_path, "venv")
    requirements_file = os.path.join(ai_engine_path, "requirements.txt")

    created_venv = create_venv_if_not_exists(venv_path)

    if os.path.exists(requirements_file):
        install_requirements(venv_path, requirements_file, created_venv)
    else:
        raise FileNotFoundError(
            f"Requirements file {requirements_file} does not exist in {ai_engine_path}"
        )

    return venv_path


def try_get_interface_definition(
    ai_engine_path: str,
) -> list[InterfaceDefinition] | None:
    definition_file = os.path.join(ai_engine_path, "model.json")
    if not os.path.exists(definition_file):
        return None
    with open(definition_file) as f:
        json_data = f.read()

    real_json = json.loads(json_data)

    some_list = [InterfaceDefinition.model_validate(item) for item in real_json]

    if len(some_list) > 0:
        return some_list

    return None
