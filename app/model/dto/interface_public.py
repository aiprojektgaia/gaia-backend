from pydantic import BaseModel

from app.db.models.interface_group import InterfaceDb


class InterfacePublic(BaseModel):
    """What clients may see of an interface: no filesystem paths, venv
    locations, module/function names or launch arguments."""

    id: int
    name: str
    description: str
    interface_group_id: int
    is_active: bool
    installed: bool

    @staticmethod
    def from_interface_db(interface: InterfaceDb) -> "InterfacePublic":
        return InterfacePublic(
            id=interface.id,
            name=interface.name,
            description=interface.description,
            interface_group_id=interface.interface_group_id,
            is_active=interface.is_active,
            installed=interface.installed,
        )
