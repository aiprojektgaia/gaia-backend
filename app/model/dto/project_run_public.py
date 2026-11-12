from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.db.models.project import RunTypesEnum, ProjectRunDb


class ProjectRunPublic(BaseModel):
    id: int
    name: str
    run_type: RunTypesEnum
    project_id: int
    is_active: bool
    status: str | None

    attributes: dict[str, Any]

    created_at: datetime
    finished_at: datetime

    @staticmethod
    def from_project_run_db(project_run: ProjectRunDb):
        return ProjectRunPublic(
            id=project_run.id,
            name=project_run.name,
            run_type=project_run.run_type,
            project_id=project_run.project_id,
            is_active=project_run.is_active,
            status=None,
            attributes=project_run.attributes,
            created_at=project_run.created_at,
            finished_at=project_run.finished_at,
    )
