import pytest

from app.db.models.interface_group import InterfaceDb
from app.tasks.task_runner import build_command_args, build_default_args


@pytest.fixture
def interface():
    return InterfaceDb(args={"a": "1", "b": "2", "c": 3})


@pytest.fixture
def interface_boolean():
    return InterfaceDb(args={"a": "1", "b": "2", "c": 3, "d": True, "e": False})


@pytest.fixture
def interface_list():
    return InterfaceDb(args={"a": "1", "b": [1, 2, 3]})


def test_command_builder_with_plain_args(interface):
    command = build_command_args(interface.args)
    assert command == ["--a=1", "--b=2", "--c=3"]


def test_command_builder_with_formatters(interface):
    command = build_command_args(
        interface.args, formatters={"c": lambda x: f"{x}x"}
    )
    assert command == ["--a=1", "--b=2", "--c=3x"]


def test_command_builder_with_boolean_values(interface_boolean):
    command = build_command_args(interface_boolean.args)
    assert command == [
        "--a=1",
        "--b=2",
        "--c=3",
        "--d=True",
        "--e=False",
    ]


def test_command_builder_with_list_values(interface_list):
    command = build_command_args(interface_list.args)
    assert command == ["--a=1", "--b=1,2,3"]


def test_build_default_args():
    assert build_default_args(
        callback_url="http://localhost:8000", output_path="/tmp/output"
    ) == {"callback_url": "http://localhost:8000", "output_path": "/tmp/output"}
