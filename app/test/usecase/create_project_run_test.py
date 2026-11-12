import pytest
from unittest import mock

from app.db.models.project import (
    RunTypesEnum,
    ProjectRunInsert,
    ProjectRunDb,
    Project,
)
from app.db.models.task import RunType, TaskType, TaskStatusEnum, TaskDb
from app.repository.project_repository import ProjectRepository
from app.repository.run_repository import ProjectRunRepository
from app.repository.run_type_repository import RunTypeRepository
from app.repository.task_repository import TaskRepository


@pytest.fixture
def task_repository_mock():
    return mock.Mock(spec=TaskRepository)


@pytest.fixture
def project_repository_mock():
    return mock.Mock(spec=ProjectRepository)


@pytest.fixture
def project_run_repository_mock():
    return mock.Mock(spec=ProjectRunRepository)


@pytest.fixture
def run_type_repository_mock():
    return mock.Mock(spec=RunTypeRepository)


global_created_tasks = []


def test_create_project_run(
    session_factory_mock,
    project_repository_mock,
    project_run_repository_mock,
    run_type_repository_mock,
    task_repository_mock,
):
    from app.usecase.create_project_run import CreateProjectRunUseCase

    use_case = CreateProjectRunUseCase(
        session_factory=session_factory_mock,
        project_repository=project_repository_mock,
        project_run_repository=project_run_repository_mock,
        run_type_repository=run_type_repository_mock,
        task_repository=task_repository_mock,
    )

    project_run_insert = ProjectRunInsert(
        name="test_create_project",
        run_type=RunTypesEnum.SegmentArea,
        attributes={
            "interface_to_use": [1, 2, 3],
            "good_stuff": "yes",
            "confidence_level": 0.95,
            "wms_server_url": "http://localhost:9600/geoserver/wms",
            "layer_name": "gaia:GOT_6393_142",
            "mpp": 0.08,
            "overlap": 10,
            "bbox": "142000,6394000,143000,6393000",
            "epsg": "EPSG:3007",
        },
        project_id=1,
    )

    # set up the mocks
    project_repository_mock.get_by_id.return_value = Project(
        id=1, name="test_project"
    )
    project_run_repository_mock.create.return_value = ProjectRunDb(
        id=11,
        name=project_run_insert.name,
        run_type=project_run_insert.run_type,
        attributes=project_run_insert.attributes,
        project_id=project_run_insert.project_id,
    )

    run_type_repository_mock.get_by_name.return_value = RunType(
        id=1,
        name=RunTypesEnum.SegmentArea,
        tasks=[
            TaskType(
                id=100,
                name="task1",
                run_type_id=1,
                order=1,
                is_interface_dependent=True,
                tasks=[],
            ),
            TaskType(
                id=101,
                name="task3",
                run_type_id=3,
                order=3,
                is_interface_dependent=False,
                tasks=[],
            ),
            TaskType(
                id=102,
                name="task2",
                run_type_id=2,
                order=2,
                is_interface_dependent=True,
                tasks=[],
            ),
        ],
    )
    task_repository_mock.create.side_effect = create_task_side_effect

    project_run = use_case.create_project_run(project_run_insert)

    assert project_run is not None
    assert global_created_tasks is not None

    total_interfaces = len(project_run_insert.attributes["interface_to_use"])

    # total = 1 to tile, 1 segmentation task per interface, 1 merge task per interface
    assert len(global_created_tasks) == (
        1 + total_interfaces * 1 + total_interfaces * 1
    )


def create_task_side_effect(*args, **kwargs):
    # print(args[0])
    task_to_insert = args[0]
    task_db = TaskDb(
        id=1000 + task_to_insert.task_type_id,
        project_run_id=task_to_insert.project_run_id,
        task_type_id=task_to_insert.task_type_id,
        interface_id=task_to_insert.interface_id,
        attributes=task_to_insert.attributes,
        input_path="",
        status=TaskStatusEnum.PENDING,
    )

    global_created_tasks.append(task_db)

    return task_db
