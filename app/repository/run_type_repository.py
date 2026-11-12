from sqlalchemy import Sequence
from sqlmodel import select


from app.db.models.task import RunType
from app.repository.base_repository import BaseRepository


class RunTypeRepository(BaseRepository):
    def get_all(self) -> Sequence[RunType]:
        return self.session.exec(select(RunType)).all()

    def get_by_id(self, run_type_id: int) -> RunType | None:
        return self.session.get(RunType, run_type_id)

    def get_by_name(self, run_type_name: str) -> RunType | None:
        statement = select(RunType).where(RunType.name == run_type_name)
        run_type = self.session.exec(statement).first()
        return run_type
