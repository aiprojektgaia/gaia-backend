from typing import List

from sqlmodel import col, select
from sqlalchemy.orm import selectinload

from app.db.models.interface_group import (
    InterfaceDb,
    InterfaceGroup,
    InterfaceInsert,
)
from app.repository.base_repository import BaseRepository


class InterfaceRepository(BaseRepository):
    def get(self, interface_id: int) -> InterfaceDb | None:
        return self.session.get(InterfaceDb, interface_id)

    def get_all(self) -> List[InterfaceDb]:
        statement = select(InterfaceDb)
        return self.session.exec(statement).all()

    def get_all_eager(self) -> List[InterfaceDb]:
        statement = select(InterfaceDb).options(
            selectinload(InterfaceDb.interface_group)
        )
        return self.session.exec(statement).all()

    def get_by_name(self, name: str) -> InterfaceDb | None:
        statement = select(InterfaceDb).where(InterfaceDb.name.ilike(name))
        return self.session.exec(statement).first()

    def get_all_by_group(self, interface_group_id: int) -> List[InterfaceDb]:
        statement = select(InterfaceDb).where(
            InterfaceDb.interface_group_id == interface_group_id
        )
        return self.session.exec(statement).all()

    def add(self, interface_to_add: InterfaceInsert) -> InterfaceDb:
        db_interface = InterfaceDb.model_validate(interface_to_add)
        self.session.add(db_interface)
        self.session.commit()
        self.session.refresh(db_interface)
        return db_interface

    def disable(self, interface_id: int) -> bool:
        interface = self.session.get(InterfaceDb, interface_id)
        if interface is None:
            return False
        interface.is_active = False
        self.session.commit()
        return True

    def delete(self, interface_id: int) -> bool:
        interface = self.session.get(InterfaceDb, interface_id)
        if interface is None:
            return False
        self.session.delete(interface)
        self.session.commit()
        return True

    def get_all_installed(self) -> List[InterfaceDb]:
        statement = select(InterfaceDb).where(InterfaceDb.installed)
        return self.session.exec(statement).all()

    def get_inactive(self) -> List[InterfaceDb]:
        statement = select(InterfaceDb).where(
            col(InterfaceDb.is_active).is_(False)
        )
        return self.session.exec(statement).all()

    def install_interface(
        self, interface_id: int, path: str, venv_path: str
    ) -> bool:
        interface = self.session.get(InterfaceDb, interface_id)
        if interface is None:
            return False
        interface.path = path
        interface.venv_path = venv_path
        interface.is_active = True
        interface.installed = True
        self.session.commit()
        return True

    def uninstall_interface(self, interface_id: int) -> bool:
        interface = self.session.get(InterfaceDb, interface_id)
        if interface is None:
            return False
        interface.is_active = False
        interface.installed = False
        self.session.commit()
        return True

    def get_by_group_name(self, group_name: str) -> List[InterfaceDb]:
        statement = (select(InterfaceDb)
                     .join(InterfaceGroup)
                     .where(
                            col(InterfaceGroup.name) == group_name,
                            col(InterfaceDb.is_active).is_(True))
                     )
        return self.session.exec(statement).all()

    # InterfaceGroup methods
    def get_group(self, interface_group_id: int) -> InterfaceGroup | None:
        return self.session.get(InterfaceGroup, interface_group_id)

    def get_group_by_name(self, group_name: str) -> InterfaceGroup | None:
        statement = select(InterfaceGroup).where(
            InterfaceGroup.name == group_name
        )
        interface_group = self.session.exec(statement).first()
        return interface_group

    def get_all_groups(self) -> list[InterfaceGroup]:
        result = self.session.exec(select(InterfaceGroup)).all()
        return list(result) if result else list()
