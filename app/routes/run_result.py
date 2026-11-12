from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from dependency_injector.wiring import inject, Provide

from app.container import Container
from app.usecase.handle_run_result import HandleRunResultUseCase

from app.db.models.task import TaskStepResultInsert

router = APIRouter(prefix="/run_result", tags=["run_result"])


@router.post("/{step_external_id}", response_class=JSONResponse)
@inject
def create_project(
    step_external_id: UUID,
    step_result: TaskStepResultInsert,
    handle_run_result: HandleRunResultUseCase = Depends(
        Provide[Container.handle_run_result_usecase]
    ),
) -> JSONResponse:
    is_handled = handle_run_result.handle(step_external_id, step_result)

    return JSONResponse(content={"handled": is_handled})
