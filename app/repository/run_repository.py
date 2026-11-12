from sqlalchemy import text
from sqlmodel import select

from app.db.models.project import ProjectRunDb, ProjectRunInsert
from app.repository.base_repository import BaseRepository


class ProjectRunRepository(BaseRepository):
    def get_by_id(self, run_id: int) -> ProjectRunDb | None:
        return self.session.get(ProjectRunDb, run_id)

    def get_by_project_id(self, project_id: int) -> list[ProjectRunDb]:
        statement = select(ProjectRunDb).where(
            ProjectRunDb.project_id == project_id
        )
        return self.session.exec(statement).all()

    def create(self, project_run: ProjectRunInsert) -> ProjectRunDb:
        db_project_run = ProjectRunDb.model_validate(project_run)
        self.session.add(db_project_run)
        self.session.commit()
        self.session.refresh(db_project_run)
        return db_project_run

    def delete(self, project_run: ProjectRunDb) -> bool:
        self.session.delete(project_run)
        return True

    def get_status(self, run_id: int) -> str:
        sql = text(f"""
            select tab.status, tab.statusInt
            from (
                select 
                    t.status, 
                    CASE 
                        WHEN t.status = 'KILLED' THEN 1
                        WHEN t.status = 'ERROR' THEN 2
                        WHEN t.status = 'PENDING' THEN 3
                        WHEN t.status = 'RUNNING' THEN 4
                        WHEN t.status = 'QUEUED' THEN 5
                        WHEN t.status = 'FINISHED' THEN 6
                        ELSE 100
                    END statusInt 
                from task t 
                where t.project_run_id = {run_id}
            ) tab
            order by tab.statusInt
            limit 1;
        """)
        # Note. Scalar takes the first column of the first row,
        # which means tab.status.
        result = self.session.execute(sql)
        status = result.scalar_one_or_none()
        return status
