import os
import uuid
from pathlib import Path

import pytest
from unittest import mock

from app.db.models.interface_group import InterfaceDb
from app.db.models.task import TaskDb, TaskStatusEnum, TaskType, TaskStepDb
from app.helpers.path_helper import (
    create_extra_folder_for_interface,
    create_task_step_input_path,
    create_task_step_output_path,
)
from app.repository.task_repository import TaskRepository
from app.repository.task_step_repository import TaskStepRepository
from app.repository.interface_repository import InterfaceRepository

from app.tasks.tasks.tile_image import ImageTiler
from app.tasks.tasks.segment_process import SegmentProcess
from app.tasks.tasks.merge_tiles import MergeTiles


@pytest.fixture
def interface():
    return InterfaceDb(
        id=10,
        name="ImageTiler",
        module_file_name="test_interface.py",
        description="This is an image tiler interface",
        args={},
        function_name="do_test",
        is_active=True,
        installed=True,
        venv_path="",
        path="",
    )


@pytest.fixture
def task_types():
    return [
        TaskType(
            id=1,
            name="TileImagesSrc",
            description="Tile images source",
            is_active=True,
            is_system=True,
            order=1,
        ),
        TaskType(
            id=2,
            name="SegmentProcess",
            description="Segment process",
            is_active=True,
            is_system=True,
            order=2,
        ),
        TaskType(
            id=3,
            name="MergeTiles",
            description="Merge of tiles",
            is_active=True,
            is_system=True,
            order=3,
        ),
    ]


@pytest.fixture
def task_repository_mock():
    return mock.Mock(spec=TaskRepository)


@pytest.fixture
def task_step_repository_mock():
    return mock.Mock(spec=TaskStepRepository)


@pytest.fixture
def interface_repository_mock():
    return mock.Mock(spec=InterfaceRepository)


@pytest.fixture
def local_test_dir(tmp_path):
    # Create a temporary directory using pytest's tmp_path fixture
    # this is the "actual" filesystem representation, that may or
    # may not match the actual interface we're testing
    storage_dir = tmp_path / "gaia" / "storage"
    interface_dir = storage_dir / "test_tiling_path"
    interface_dir.mkdir()
    output_dir = interface_dir / "1"
    output_dir.mkdir()
    file_1 = output_dir / "file_1.tif"
    file_1.write_text("1")
    file_2 = output_dir / "file_2.tif"
    file_2.write_text("2")
    file_3 = output_dir / "file_3.tif"
    file_3.write_text("3")
    files = [
        f
        for f in os.listdir(output_dir)
        if os.path.isfile(os.path.join(output_dir, f))
    ]
    print("files: ", files)
    return tmp_path


task_step_id_counter = 1


def get_next_step_id():
    global task_step_id_counter
    task_step_id_counter += 1
    return task_step_id_counter


def task_step_create_mock(step_to_insert):
    return TaskStepDb(
        id=get_next_step_id(),
        task_id=step_to_insert.task_id,
        task_type_id=step_to_insert.task_type_id,
        interface_id=step_to_insert.interface_id,
        status=step_to_insert.status,
        external_id=step_to_insert.external_id,
        input_path=step_to_insert.input_path,
    )


def test_create_tile_images_src_step(
    interface, interface_repository_mock, task_step_repository_mock
):
    step_id_to_start = task_step_id_counter + 1
    interface_repository_mock.get_by_name.return_value = interface
    # interface_repository_mock.set_session.return_value = None
    task_step_repository_mock.create = task_step_create_mock
    # task_step_repository_mock.set_session.return_value = None

    task_db = TaskDb(
        input_path="test_input_path",
        status=TaskStatusEnum.QUEUED,
        task_type_id=1,
    )

    # step = task_resolver.TileImagesSrc(task_db, interface_repository_mock, task_step_repository_mock)
    step = ImageTiler.handle(
        task_db, interface_repository_mock, task_step_repository_mock
    )
    assert step is not None
    assert len(step) == 1
    assert step[0].status == TaskStatusEnum.QUEUED
    assert step[0].input_path == f"test_input_path\\{step_id_to_start}"


def test_create_segment_process_step_too_early(
    task_types, task_repository_mock, task_step_repository_mock
):
    tiling_task_db = TaskDb(
        project_run_id=111,
        input_path="test_segment_path\\1",
        status=TaskStatusEnum.QUEUED,
        task_type_id=1,  # ImageTiler
    )
    segment_task_db = TaskDb(
        project_run_id=111,
        input_path="test_segment_path\\2",
        status=TaskStatusEnum.QUEUED,
        task_type_id=2,  # SegmentProcess
    )
    merge_task_db = TaskDb(
        project_run_id=111,
        input_path="test_segment_path\\3",
        status=TaskStatusEnum.QUEUED,
        task_type_id=3,  # MergeTiles
    )
    tasks = [tiling_task_db, segment_task_db, merge_task_db]

    tiling_step_db = TaskStepDb(
        input_path=f"{tiling_task_db.input_path}\\{tiling_task_db.id}",
        status=TaskStatusEnum.RUNNING,
        task_type_id=1,
    )
    tiling_step_db.output_path = tiling_task_db.input_path
    tiling_task_db.steps.append(tiling_step_db)

    task_repository_mock.get_by_run_id.return_value = tasks

    # how to assert an exception?
    with pytest.raises(Exception):
        # task_resolver.SegmentProcess(segment_task_db, task_repository_mock, task_step_repository_mock)
        SegmentProcess.handle(
            segment_task_db, task_repository_mock, task_step_repository_mock
        )


def test_create_segment_process_step(
    task_types, task_repository_mock, task_step_repository_mock, local_test_dir
):
    step_id_to_start = task_step_id_counter + 1
    test_tiling_path = (
        local_test_dir / "gaia" / "storage" / "test_tiling_path" / "1"
    )

    tiling_task_db = TaskDb(
        project_run_id=111,
        input_path=test_tiling_path,
        status=TaskStatusEnum.FINISHED,
        task_type_id=1,  # ImageTiler
        task_type=task_types[0],
    )
    segment_task_db = TaskDb(
        project_run_id=111,
        input_path="test_segment_path",
        status=TaskStatusEnum.QUEUED,
        task_type_id=2,  # SegmentProcess
        task_type=task_types[1],
    )
    merge_task_db = TaskDb(
        project_run_id=111,
        input_path="test_merge_path",
        status=TaskStatusEnum.QUEUED,
        task_type_id=3,  # MergeTiles
        task_type=task_types[2],
    )
    tasks = [tiling_task_db, segment_task_db, merge_task_db]

    tiling_step_db = TaskStepDb(
        input_path=f"{tiling_task_db.input_path}",
        status=TaskStatusEnum.FINISHED,
        task_type_id=1,
    )
    interface_list = [666]
    segment_task_db.attributes = {"interface_to_use": interface_list}
    num_of_interfaces = len(interface_list)

    tiling_step_db.output_path = tiling_task_db.input_path
    tiling_task_db.steps.append(tiling_step_db)

    task_repository_mock.get_by_run_id.return_value = tasks
    task_step_repository_mock.create = task_step_create_mock

    # steps_created = task_resolver.SegmentProcess(segment_task_db, task_repository_mock, task_step_repository_mock)
    steps_created = SegmentProcess.handle(
        segment_task_db, task_repository_mock, task_step_repository_mock
    )

    assert steps_created is not None
    assert len(steps_created) == 3 * num_of_interfaces
    assert steps_created[0].status == TaskStatusEnum.QUEUED
    first_interface_id = interface_list[0]
    assert (
        steps_created[0].output_path
        == f"test_segment_path\\interface_{first_interface_id}\\{step_id_to_start}\\output"
    )
    # get all the steps from steps_created which input_path contains "file_1.txt"
    steps_for_file_1 = [
        step
        for step in steps_created
        if step.input_path.find("file_1.tif") != -1
    ]
    steps_for_file_2 = [
        step
        for step in steps_created
        if step.input_path.find("file_2.tif") != -1
    ]
    steps_for_file_3 = [
        step
        for step in steps_created
        if step.input_path.find("file_3.tif") != -1
    ]
    assert (
        len(steps_for_file_1)
        == len(steps_for_file_2)
        == len(steps_for_file_3)
        == num_of_interfaces
    )

    # assert that all the files in the list steps_for_file_x have the same input_path
    assert all(
        step.input_path == steps_for_file_1[0].input_path
        for step in steps_for_file_1
    )
    assert all(
        step.input_path == steps_for_file_2[0].input_path
        for step in steps_for_file_2
    )
    assert all(
        step.input_path == steps_for_file_3[0].input_path
        for step in steps_for_file_3
    )


def test_create_merge_tile_steps(
    task_types, task_repository_mock, task_step_repository_mock, local_test_dir
):
    test_path = local_test_dir / "gaia" / "storage" / "test_merge_tile_path"
    test_path.exists() or test_path.mkdir()

    test_tiling_path = test_path / "tiling"
    test_tiling_path.exists() or test_tiling_path.mkdir()
    tiling_task_db = TaskDb(
        project_run_id=111,
        input_path=str(test_tiling_path),
        status=TaskStatusEnum.FINISHED,
        task_type_id=1,  # ImageTiler
        task_type=task_types[0],
    )
    test_segmenting_path = test_path / "segmenting"
    test_segmenting_path.exists() or test_segmenting_path.mkdir()
    segment_task_db = TaskDb(
        project_run_id=111,
        input_path=str(test_segmenting_path),
        status=TaskStatusEnum.FINISHED,
        task_type_id=2,  # SegmentProcess
        task_type=task_types[1],
    )
    test_merging_path = test_path / "merging"
    test_merging_path.exists() or test_merging_path.mkdir()
    merge_task_db = TaskDb(
        project_run_id=111,
        input_path=str(test_merging_path),
        status=TaskStatusEnum.QUEUED,
        task_type_id=3,  # MergeTiles
        task_type=task_types[2],
    )
    tasks = [tiling_task_db, segment_task_db, merge_task_db]

    tiling_step_db = TaskStepDb(
        input_path=f"{tiling_task_db.input_path}",
        status=TaskStatusEnum.FINISHED,
        task_type_id=1,
    )
    interface_list = [10, 2, 666]
    segment_task_db.attributes = {"interface_to_use": interface_list}
    merge_task_db.attributes = {"interface_to_use": interface_list}
    num_of_interfaces = len(interface_list)

    tiling_step_db.output_path = tiling_task_db.input_path
    tiling_task_db.steps.append(tiling_step_db)

    task_repository_mock.get_by_run_id.return_value = tasks
    task_step_repository_mock.create = task_step_create_mock

    tiles = ["file_1.txt", "file_2.txt", "file_3.txt"]
    create_output_data_for_segmentation(segment_task_db, tiles)

    # steps_created = task_resolver.MergeTiles(segment_task_db, task_repository_mock, task_step_repository_mock)
    steps_created = MergeTiles.handler(
        merge_task_db, task_repository_mock, task_step_repository_mock
    )
    assert steps_created is not None
    assert len(steps_created) == num_of_interfaces
    assert steps_created[0].status == TaskStatusEnum.QUEUED

    for interface_id in interface_list:
        steps_for_interface = [
            step
            for step in steps_created
            if step.input_path.find(f"interface_{interface_id}") != -1
        ]
        assert len(steps_for_interface) == 1

        expected_input_path = create_extra_folder_for_interface(
            segment_task_db.input_path, interface_id
        )
        le_step = steps_for_interface[0]
        assert le_step.input_path == expected_input_path


def create_output_data_for_segmentation(segment_task_db, tiles: list[str]):
    interface_list = segment_task_db.attributes["interface_to_use"]

    # assuming there are 3 tiles to handle
    # I will create 3 * len(interface_list) amount of steps
    # per step an output path and file will be created
    steps = []
    for interface_id in interface_list:
        input_path = create_extra_folder_for_interface(
            segment_task_db.input_path, interface_id
        )
        for image_file in tiles:
            step_added = TaskStepDb(
                task_id=segment_task_db.id,
                task_type_id=segment_task_db.task_type_id,
                interface_id=interface_id,
                status=TaskStatusEnum.FINISHED,
                external_id=uuid.uuid4(),
                input_path=input_path,
            )

            # need to create this one to be able to create the output path
            step_added.input_path = create_task_step_input_path(step_added)
            step_added.output_path = create_task_step_output_path(step_added)

            file_to_write = Path(step_added.output_path) / image_file
            file_to_write.write_text(f"I am file '{image_file}'")

            steps.append(step_added)

    segment_task_db.steps = steps
