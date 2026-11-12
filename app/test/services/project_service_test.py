import pytest
from app.db.models.project import Project, ProjectBase
from app.repository.project_repository import ProjectRepository
from app.service.project_service import ProjectService
from unittest import mock


@pytest.fixture
def empty_project_service(session_factory_mock):
    project_repository_mock = mock.Mock(spec=ProjectRepository)
    project_repository_mock.get_all.return_value = []
    project_repository_mock.get_by_id.return_value = None
    project_repository_mock.get_by_name.return_value = []
    project_repository_mock.add_project.side_effect = lambda x: x
    project_repository_mock.delete_project.return_value = False
    return ProjectService(
        session_factory=session_factory_mock,
        project_repository=project_repository_mock,
    )


@pytest.fixture
def project_service_with_projects(session_factory_mock):
    project_repository_mock = mock.Mock(spec=ProjectRepository)
    projects = [
        Project(
            id=1,
            name="Test Project",
            description="Test Description",
            created_by="Test User",
            attributes={"key": "value"},
        ),
        Project(
            id=2,
            name="Test Project 2",
            description="Test Description 2",
            created_by="Test User 2",
            attributes={"key": "value"},
        ),
    ]

    project_repository_mock.get_all.return_value = projects
    project_repository_mock.get_by_id.side_effect = lambda id: next(
        (p for p in projects if p.id == id), None
    )
    project_repository_mock.get_by_name.return_value = projects
    project_repository_mock.add_project.side_effect = lambda x: Project(
        id=len(projects) + 1, **x.model_dump()
    )
    project_repository_mock.delete_project.return_value = True
    return ProjectService(
        session_factory=session_factory_mock,
        project_repository=project_repository_mock,
    )


def test_get_all_projects(project_service_with_projects):
    projects = project_service_with_projects.get_all_projects()
    assert len(projects) == 2
    assert projects[0].id == 1
    assert projects[1].id == 2


def test_get_project_by_id(project_service_with_projects):
    project = project_service_with_projects.get_project_by_id(2)
    assert project is not None
    assert project.id == 2


def test_add_project(project_service_with_projects):
    project = project_service_with_projects.create_project(
        ProjectBase(
            name="Test Project 3",
            description="Test Description 3",
            created_by="Test User 3",
            attributes={"key": "value"},
        )
    )
    assert project is not None
    assert project.id == 3


def test_delete_project(project_service_with_projects):
    result = project_service_with_projects.delete_project(1)
    assert result is True
