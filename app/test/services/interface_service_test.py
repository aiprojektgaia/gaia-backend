import pytest
from unittest import mock
from app.db.models.interface_group import InterfaceDb
from app.service.interface_service import InterfaceService
from app.repository.interface_repository import InterfaceRepository


@pytest.fixture
def interface():
    return InterfaceDb(
        name="test_interface",
        module_file_name="test_interface.py",
        description="This is a testing interface",
        args={},
        function_name="do_test",
        is_active=True,
        installed=True,
        venv_path="",
        path="",
    )


@pytest.fixture
def interface_repository_mock():
    return mock.Mock(spec=InterfaceRepository)


@pytest.fixture
def interface_service(session_factory_mock, interface_repository_mock):
    return InterfaceService(session_factory_mock, interface_repository_mock)


@pytest.fixture
def local_test_dir(tmp_path):
    # Create a temporary directory using pytest's tmp_path fixture
    # this is the "actual" filesystem representation, that may or
    # may not match the actual interface we're testing
    interface_dir = tmp_path / "interfaces"
    interface_dir.mkdir()
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    main_file = interface_dir / "main.py"
    main_file.write_text("")
    return tmp_path


def test_is_interface_runnable(interface_service, interface, local_test_dir):
    interface.path = str(local_test_dir / "interfaces")
    interface.venv_path = str(local_test_dir / "venv")
    interface.module_file_name = str(local_test_dir / "interfaces" / "main.py")

    result = interface_service.is_interface_runnable(interface)
    assert result is True


def test_is_interface_runnable_raises_error_if_not_installed(
    interface_service, interface
):
    interface.installed = False
    with pytest.raises(ValueError):
        interface_service.is_interface_runnable(interface)


def test_is_interface_runnable_raises_error_if_not_active(
    interface_service, interface
):
    interface.is_active = False
    with pytest.raises(ValueError):
        interface_service.is_interface_runnable(interface)


def test_is_interface_runnable_raises_error_if_path_does_not_exist(
    interface_service, interface
):
    interface.path = "non_existent_path"
    with pytest.raises(FileNotFoundError):
        interface_service.is_interface_runnable(interface)


def test_is_interface_runnable_raises_error_if_venv_path_does_not_exist(
    interface_service, interface, local_test_dir
):
    interface.path = str(local_test_dir / "interfaces")
    interface.venv_path = "non_existent_path"
    with pytest.raises(FileNotFoundError):
        interface_service.is_interface_runnable(interface)


def test_is_interface_runnable_raises_error_if_module_file_does_not_exist(
    interface_service, interface, local_test_dir
):
    interface.path = str(local_test_dir / "interfaces")
    interface.venv_path = str(local_test_dir / "venv")
    interface.module_file_name = "non_existent_path.py"
    with pytest.raises(FileNotFoundError):
        interface_service.is_interface_runnable(interface)
