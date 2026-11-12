from contextlib import AbstractContextManager
from typing import Callable, List

from sqlmodel import Session
from app.db.models.project import Project
from app.repository.project_repository import ProjectRepository
from app.helpers.wms_policy import validate_wms_url


class ProjectService:
    def __init__(
        self,
        session_factory: Callable[..., AbstractContextManager[Session]],
        project_repository: ProjectRepository,
    ) -> None:
        self.session_factory = session_factory
        self.project_repository = project_repository

    def get_all_projects(self) -> List[Project]:
        with self.session_factory() as session:
            self.project_repository.set_session(session)
            return self.project_repository.get_all()

    def get_project_by_id(self, project_id: int) -> Project | None:
        with self.session_factory() as session:
            self.project_repository.set_session(session)
            return self.project_repository.get_by_id(project_id)

    def create_project(self, project: Project) -> Project:
        attributes = project.attributes or {}
        if "wms_server_url" in attributes:
            validate_wms_url(attributes["wms_server_url"])
        with self.session_factory() as session:
            self.project_repository.set_session(session)
            project_db = self.project_repository.add_project(project)
            session.commit()
            session.refresh(project_db)
            return project_db

    def delete_project(self, project_id: int) -> bool:
        with self.session_factory() as session:
            self.project_repository.set_session(session)
            exists_project = self.project_repository.get_by_id(project_id)
            if exists_project is None:
                raise ValueError("Project does not exist")

            self.project_repository.delete_project(project_id)
            session.commit()
            return True
