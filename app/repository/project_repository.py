from sqlmodel import select
from app.db.models.project import Project, ProjectBase
from app.repository.base_repository import BaseRepository


class ProjectRepository(BaseRepository):
    def get_all(self) -> list[Project]:
        result = self.session.exec(select(Project)).all()
        return list(result) if result else list()

    def get_by_id(self, project_id: int) -> Project | None:
        return self.session.get(Project, project_id)

    def get_by_name(self, project_name: str) -> list[Project]:
        statement = select(Project).where(Project.name == project_name)
        result = self.session.exec(statement).all()
        return list(result) if result else []

    def add_project(self, project: ProjectBase) -> Project:
        db_project = Project.model_validate(project)
        self.session.add(db_project)
        return db_project

    def delete_project(self, project_id: int) -> bool:
        project = self.session.get(Project, project_id)
        if project is None:
            return False
        self.session.delete(project)
        return True
