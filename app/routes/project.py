import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from dependency_injector.wiring import inject, Provide
from app.container import Container
from app.db.models.project import (
    Project,
    ProjectBase,
    ProjectPublicSimple,
)
from app.service.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[ProjectPublicSimple])
@inject
def get_all_project(
    project_service: ProjectService = Depends(
        Provide[Container.project_service]
    ),
) -> List[Project]:
    logging.info("get all project")
    all_projects = project_service.get_all_projects()
    return all_projects


@router.get("/{project_id}", response_model=ProjectPublicSimple)
@inject
def get_project(
    project_id: int,
    project_service: ProjectService = Depends(
        Provide[Container.project_service]
    ),
) -> Project | None:
    logging.info(f"get project with id {project_id}")
    return project_service.get_project_by_id(project_id)


@router.put("", response_model=ProjectPublicSimple)
@inject
def create_project(
    project_create: ProjectBase,
    project_service: ProjectService = Depends(
        Provide[Container.project_service]
    ),
) -> Project:
    logging.info(f"creating project named: {project_create.name}")

    try:
        updated_project = project_service.create_project(project_create)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    logging.info(f"created project with id: {updated_project}")
    return updated_project


@router.delete("/{project_id}", response_class=JSONResponse)
@inject
def delete_project(
    project_id: int,
    project_service: ProjectService = Depends(
        Provide[Container.project_service]
    ),
) -> JSONResponse:
    logging.info(f"deleting project with id {project_id}")
    try:
        result = project_service.delete_project(project_id)
        return JSONResponse(content={"result": result})
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")
