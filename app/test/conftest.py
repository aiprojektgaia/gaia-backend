"""
Put fixtures in here so they can be shared amongst tests
"""

import os
from unittest import mock
import pytest
from sqlmodel import Session

from app.repository.run_repository import ProjectRunRepository
from app.repository.task_repository import TaskRepository


@pytest.fixture
def session_factory_mock():
    # Create a session mock
    session_mock = mock.Mock(spec=Session)

    # Create a context manager mock that properly handles __enter__ and __exit__
    context_manager = mock.MagicMock()
    context_manager.__enter__.return_value = session_mock
    context_manager.__exit__.return_value = None

    # Create session factory that returns the context manager
    session_factory_mock = mock.Mock(return_value=context_manager)

    return session_factory_mock


@pytest.fixture(autouse=True)
def set_env(tmp_path):
    gaia_dir = tmp_path / "gaia"
    gaia_dir.mkdir()
    engines_dir = gaia_dir / "engines"
    engines_dir.mkdir()
    storage_dir = gaia_dir / "storage"
    storage_dir.mkdir()
    os.environ["MODEL_BASE_PATH"] = f"{engines_dir}"
    os.environ["STORAGE_PATH"] = f"{storage_dir}"
    os.environ["POSTGRES_USER"] = "user"
    os.environ["POSTGRES_PASSWORD"] = "p@ssw0rd"
    os.environ["POSTGRES_SERVER"] = "localhost"
    os.environ["POSTGRES_PORT"] = "1234"
    os.environ["POSTGRES_DB"] = "myDb"
    os.environ["DEBUG"] = "true"
    # Required by Config; any value >= 16 chars works for tests.
    os.environ["GAIA_API_KEY"] = "test-api-key-not-a-real-secret"


@pytest.fixture
def task_repository_mock():
    return mock.Mock(spec=TaskRepository)


@pytest.fixture
def project_run_repository_mock():
    return mock.Mock(spec=ProjectRunRepository)
