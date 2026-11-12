from datetime import datetime
import logging
import time
import traceback
import io

from typing import List, Sequence
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from dependency_injector.wiring import inject, Provide

from app.config import get_config
from app.container import Container
from app.db.models.project import ProjectRunDb, ProjectRunInsert
from app.model.dto.project_run_public import ProjectRunPublic

from app.model.project_run_status import ProjectRunStatus
from app.service.project_run_service import ProjectRunService
from app.usecase.create_project_run import CreateProjectRunUseCase
from app.usecase.download_run_result import DownloadRunResultUseCase
from app.usecase.get_project_run_status import GetProjectRunStatusUseCase

router = APIRouter(prefix="/runs", tags=["project_runs"])


@router.get("", response_model=list[ProjectRunPublic])
@inject
def get_all_project_runs(
    project_id: int,
    project_run_service: ProjectRunService = Depends(
        Provide[Container.project_run_service]
    ),
) -> list[ProjectRunPublic]:
    logging.info(f"get all project runs for id {project_id}")
    all_project_runs = project_run_service.get_project_runs(project_id)
    return all_project_runs


@router.get("/{run_id}", response_model=ProjectRunPublic)
@inject
def get_by_id(
    run_id: int,
    project_run_service: ProjectRunService = Depends(
        Provide[Container.project_run_service]
    ),
) -> ProjectRunPublic:
    logging.info(f"get project run with id {run_id}")
    project_run = project_run_service.get_project_run(run_id)
    if project_run is None:
        raise HTTPException(status_code=404, detail="Project run not found")
    return ProjectRunPublic.from_project_run_db(project_run)


@router.post("", response_model=ProjectRunPublic)
@inject
def create_run(
    project_run: ProjectRunInsert,
    create_project_run_usecase: CreateProjectRunUseCase = Depends(
        Provide[Container.create_project_run_usecase]
    ),
) -> ProjectRunPublic | JSONResponse:
    logging.info(f"creating project run named: {project_run.name}")
    try:
        new_run: ProjectRunDb = create_project_run_usecase.create_project_run(
            project_run
        )
        return ProjectRunPublic.from_project_run_db(new_run)
    except ValueError as ve:
        logging.error(traceback.format_exc())
        # 400, not 200: the run was not created
        return JSONResponse(status_code=400, content={"error": str(ve)})


@router.delete("/{run_id}", response_class=JSONResponse)
@inject
def delete_run(
    run_id: int,
    project_run_service: ProjectRunService = Depends(
        Provide[Container.project_run_service]
    ),
) -> JSONResponse:
    logging.info(f"deleting project run with id {run_id}")
    deleted = project_run_service.delete_project_run(run_id)
    return JSONResponse(content={"result": deleted})


@router.get("/{run_id}/download")
@inject
def download_run_result(
    run_id: int,
    download_run_result_usecase: DownloadRunResultUseCase = Depends(
        Provide[Container.download_run_result_usecase]
    ),
) -> StreamingResponse:
    logging.info(f"downloading run result for id {run_id}")
    try:
        archive = download_run_result_usecase.handle(run_id)
    except ValueError as ve:
        return JSONResponse(status_code=409, content={"error": str(ve)})

    deadline = time.monotonic() + get_config().DOWNLOAD_MAX_SECONDS

    def iterate_and_close():
        # stream from the temp file in chunks; closing deletes it and frees
        # the download slot
        try:
            while chunk := archive.read(1024 * 1024):
                if time.monotonic() > deadline:
                    logging.warning(f"download of run {run_id} exceeded its time limit")
                    break
                yield chunk
        finally:
            archive.close()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"run_{run_id}_files_{timestamp}.zip"

    return StreamingResponse(
        iterate_and_close(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{run_id}/status", response_model=ProjectRunStatus)
@inject
def get_run_status(
    run_id: int,
    get_project_run_status_usecase: GetProjectRunStatusUseCase = Depends(
        Provide[Container.get_project_run_status_usecase]
    ),
) -> ProjectRunStatus:
    logging.info(f"getting status for project run with id {run_id}")
    return get_project_run_status_usecase.get_project_run_status(run_id)
