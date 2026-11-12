import os
import uuid
import pytest
import sys

from app.config import get_callback_url
from app.db.models.interface_group import InterfaceDb
from app.tasks.task_runner import (
    build_default_args,
    prepare_command,
)


@pytest.fixture
def mock_win_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    return sys.platform


@pytest.fixture
def mock_unix_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    return sys.platform


@pytest.fixture
def mock_paths(monkeypatch):
    def mock_exists(path):
        return True

    def mock_join(*args):
        return "/".join(args)

    monkeypatch.setattr(os.path, "exists", mock_exists)
    monkeypatch.setattr(os.path, "join", mock_join)
    return os.path


@pytest.fixture
def mock_interface():
    interface = InterfaceDb(
        id=uuid.uuid4(),
        name="TestInterface",
        module_file_name="test_interface.py",
        args={"a": "1", "b": "2", "c": 3},
        function_name="test_function",
        installed=True,
        venv_path="",
        path="",
    )
    return interface


def test_prepare_command_win(mock_win_platform, mock_paths, mock_interface):
    command = prepare_command(mock_interface, "mock_path", {"d": 4})
    assert command == [
        "/Scripts/python.exe",
        mock_interface.module_file_name,
        "--a=1",
        "--b=2",
        "--c=3",
        "--d=4",
    ]


def test_prepare_command_unix(mock_unix_platform, mock_paths, mock_interface):
    command = prepare_command(mock_interface, "mock_path", {"d": 4})
    assert command == [
        "/bin/python",
        mock_interface.module_file_name,
        "--a=1",
        "--b=2",
        "--c=3",
        "--d=4",
    ]


def test_prepare_command_without_additional_arguments(
    mock_unix_platform, mock_paths, mock_interface
):
    command = prepare_command(mock_interface, "mock_path")
    assert command == [
        "/bin/python",
        mock_interface.module_file_name,
        "--a=1",
        "--b=2",
        "--c=3",
    ]


def test_prepare_command_with_not_installed_interface(mock_interface):
    with pytest.raises(ValueError) as e:
        mock_interface.installed = False
        prepare_command(mock_interface, "mock_path", {"d": 4})
        assert str(e.value).contains("Interface is not installed")


def test_prepare_command_with_not_active_interface(mock_interface):
    with pytest.raises(ValueError) as e:
        mock_interface.is_active = False
        prepare_command(mock_interface, "mock_path", {"d": 4})
        assert str(e.value).contains("Interface is not active")


def test_prepare_command_full_path_not_found(mock_interface):
    with pytest.raises(FileNotFoundError) as e:
        prepare_command(mock_interface, "mock_path", {"d": 4})
        assert str(e.value).contains("Path mock_path does not exist")


def test_prepare_command_with_default_args(
    mock_win_platform, mock_paths, mock_interface
):
    command = prepare_command(
        mock_interface,
        "mock_path",
        build_default_args(
            callback_url=get_callback_url(mock_interface.id),
            output_path="/tmp/output",
        ),
    )
    assert command == [
        "/Scripts/python.exe",
        mock_interface.module_file_name,
        "--a=1",
        "--b=2",
        "--c=3",
        f"--callback-url=http://localhost:8000/run_result/{mock_interface.id}",
        "--output-path=/tmp/output",
    ]
