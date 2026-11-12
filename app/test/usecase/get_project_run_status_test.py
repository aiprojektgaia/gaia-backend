import pytest

from app.db.models.project import (
    RunTypesEnum,
    ProjectRunDb,
)
from app.db.models.task import TaskStatusEnum, TaskDb, TaskType


@pytest.fixture
def use_case(
    session_factory_mock, project_run_repository_mock, task_repository_mock
):
    from app.usecase.get_project_run_status import GetProjectRunStatusUseCase

    return GetProjectRunStatusUseCase(
        session_factory=session_factory_mock,
        project_run_repository=project_run_repository_mock,
        task_repository=task_repository_mock,
    )


@pytest.fixture
def mock_project_run(project_run_repository_mock):
    project_run = ProjectRunDb(
        id=11,
        name="test_project_run",
        run_type=RunTypesEnum.SegmentArea,
        attributes={"interface_to_use": [1, 2, 3]},
        project_id=1,
    )
    project_run_repository_mock.get_by_id.return_value = project_run
    return project_run


def test_get_project_run_status_pending(use_case, task_repository_mock):
    task_repository_mock.get_by_run_id.return_value = [
        TaskDb(
            id=1,
            name="task1",
            status=TaskStatusEnum.PENDING,
            task_type=TaskType(id=1, name="task_type_1", run_type_id=1),
        )
    ]
    task_repository_mock.get_total_finished_subtasks.return_value = 0

    status = use_case.get_project_run_status(11)

    assert status is not None
    assert status.message == "Project run is waiting to be processed"
    assert status.status == TaskStatusEnum.PENDING
    assert status.total_tasks == 1
    assert status.finished_tasks == 0


def test_get_project_run_status_processing(
    session_factory_mock, project_run_repository_mock, task_repository_mock
):
    from app.usecase.get_project_run_status import GetProjectRunStatusUseCase

    use_case = GetProjectRunStatusUseCase(
        session_factory=session_factory_mock,
        project_run_repository=project_run_repository_mock,
        task_repository=task_repository_mock,
    )

    # set up the mocks
    project_run_repository_mock.get_by_id.return_value = ProjectRunDb(
        id=11,
        name="test_project_run",
        run_type=RunTypesEnum.SegmentArea,
        attributes={"interface_to_use": [1, 2, 3]},
        project_id=1,
    )

    task_type=TaskType(id=1, name="task_type_1", run_type_id=1)
    task_repository_mock.get_by_run_id.return_value = [
        TaskDb(
            id=1,
            name="task1",
            status=TaskStatusEnum.RUNNING,
            task_type=task_type,
        ),
        TaskDb(
            id=2,
            name="task2",
            status=TaskStatusEnum.QUEUED,
            task_type=task_type,
        ),
    ]
    task_repository_mock.get_total_finished_subtasks.return_value = 0

    status = use_case.get_project_run_status(11)

    assert status is not None
    assert status.message == "Project tasks are processing"
    assert status.status == TaskStatusEnum.RUNNING
    assert status.total_tasks == 2
    assert status.finished_tasks == 0


def test_get_project_run_status_error(
    session_factory_mock, project_run_repository_mock, task_repository_mock
):
    from app.usecase.get_project_run_status import GetProjectRunStatusUseCase

    use_case = GetProjectRunStatusUseCase(
        session_factory=session_factory_mock,
        project_run_repository=project_run_repository_mock,
        task_repository=task_repository_mock,
    )

    # set up the mocks
    project_run_repository_mock.get_by_id.return_value = ProjectRunDb(
        id=11,
        name="test_project_run",
        run_type=RunTypesEnum.SegmentArea,
        attributes={"interface_to_use": [1, 2, 3]},
        project_id=1,
    )

    task_type=TaskType(id=1, name="task_type_1", run_type_id=1)
    task_repository_mock.get_by_run_id.return_value = [
        TaskDb(
            id=1,
            name="task1",
            status=TaskStatusEnum.ERROR,
            task_type=task_type,
        ),
        TaskDb(
            id=2,
            name="task2",
            status=TaskStatusEnum.QUEUED,
            task_type=task_type,
        ),
    ]
    task_repository_mock.get_total_finished_subtasks.return_value = 0

    status = use_case.get_project_run_status(11)

    assert status is not None
    assert status.message == "Project tasks has errors"
    assert status.status == TaskStatusEnum.ERROR
    assert status.finished_tasks == 0


def test_get_project_run_status_killed(
    session_factory_mock, project_run_repository_mock, task_repository_mock
):
    from app.usecase.get_project_run_status import GetProjectRunStatusUseCase

    use_case = GetProjectRunStatusUseCase(
        session_factory=session_factory_mock,
        project_run_repository=project_run_repository_mock,
        task_repository=task_repository_mock,
    )

    # set up the mocks
    project_run_repository_mock.get_by_id.return_value = ProjectRunDb(
        id=11,
        name="test_project_run",
        run_type=RunTypesEnum.SegmentArea,
        attributes={"interface_to_use": [1, 2, 3]},
        project_id=1,
    )
    task_repository_mock.get_total_finished_subtasks.return_value = 0

    task_type = TaskType(id=1, name="task_type_1", run_type_id=1)
    task_repository_mock.get_by_run_id.return_value = [
        TaskDb(
            id=1,
            name="task1",
            status=TaskStatusEnum.ERROR,
            task_type=task_type,
        ),
        TaskDb(
            id=2,
            name="task2",
            status=TaskStatusEnum.KILLED,
            task_type=task_type,
        ),
    ]

    status = use_case.get_project_run_status(11)

    assert status is not None
    assert status.message == "Project tasks has timed out"
    assert status.status == TaskStatusEnum.KILLED
    assert status.finished_tasks == 0


def test_get_project_run_status_remaining(
    session_factory_mock, project_run_repository_mock, task_repository_mock
):
    from app.usecase.get_project_run_status import GetProjectRunStatusUseCase

    use_case = GetProjectRunStatusUseCase(
        session_factory=session_factory_mock,
        project_run_repository=project_run_repository_mock,
        task_repository=task_repository_mock,
    )

    # set up the mocks
    project_run_repository_mock.get_by_id.return_value = ProjectRunDb(
        id=11,
        name="test_project_run",
        run_type=RunTypesEnum.SegmentArea,
        attributes={"interface_to_use": [1, 2, 3]},
        project_id=1,
    )

    task_type = TaskType(id=1, name="task_type_1", run_type_id=1)
    task_repository_mock.get_by_run_id.return_value = [
        TaskDb(
            id=1,
            name="task1",
            status=TaskStatusEnum.RUNNING,
            task_type=task_type,
        ),
        TaskDb(
            id=2,
            name="task2",
            status=TaskStatusEnum.QUEUED,
            task_type=task_type,
        ),
        TaskDb(
            id=3,
            name="task3",
            status=TaskStatusEnum.FINISHED,
            task_type=task_type,
        ),
        TaskDb(
            id=4,
            name="task4",
            status=TaskStatusEnum.FINISHED,
            task_type=task_type,
        ),
    ]
    task_repository_mock.get_total_finished_subtasks.return_value = 2

    status = use_case.get_project_run_status(11)

    assert status is not None
    assert status.message == "Project tasks are processing"
    assert status.status == TaskStatusEnum.RUNNING
    assert status.finished_tasks == 2
    assert status.total_tasks == 4


def test_get_project_run_status_remaining_different_order(
    session_factory_mock, project_run_repository_mock, task_repository_mock
):
    from app.usecase.get_project_run_status import GetProjectRunStatusUseCase

    use_case = GetProjectRunStatusUseCase(
        session_factory=session_factory_mock,
        project_run_repository=project_run_repository_mock,
        task_repository=task_repository_mock,
    )

    # set up the mocks
    project_run_repository_mock.get_by_id.return_value = ProjectRunDb(
        id=11,
        name="test_project_run",
        run_type=RunTypesEnum.SegmentArea,
        attributes={"interface_to_use": [1, 2, 3]},
        project_id=1,
    )

    task_type=TaskType(id=1, name="task_type_1", run_type_id=1)
    task_repository_mock.get_by_run_id.return_value = [
        TaskDb(
            id=1,
            name="task1",
            status=TaskStatusEnum.QUEUED,
            task_type=task_type,
        ),
        TaskDb(
            id=2,
            name="task2",
            status=TaskStatusEnum.FINISHED,
            task_type=task_type,
        ),
        TaskDb(
            id=3,
            name="task3",
            status=TaskStatusEnum.FINISHED,
            task_type=task_type,
        ),
        TaskDb(
            id=4,
            name="task4",
            status=TaskStatusEnum.QUEUED,
            task_type=task_type,
        ),
    ]
    task_repository_mock.get_total_finished_subtasks.return_value = 2

    status = use_case.get_project_run_status(11)

    assert status is not None
    assert status.status == TaskStatusEnum.QUEUED
    assert status.message == "Project tasks are queued"
    assert status.finished_tasks == 2
    assert status.total_tasks == 4
