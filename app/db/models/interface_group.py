from typing import Any, List
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import JSON


class InterfaceGroup(SQLModel, table=True):
    __tablename__ = "interface_group"
    id: int = Field(default=None, primary_key=True, index=True)
    name: str = Field(nullable=False)
    interfaces: List["InterfaceDb"] = Relationship(
        back_populates="interface_group"
    )


### Interface: (external models)


class InterfaceInsert(SQLModel):
    name: str = Field(nullable=False)
    interface_group_id: int = Field(
        nullable=False, foreign_key="interface_group.id"
    )
    """path is the absolute path to the interface"""
    path: str = Field(index=True, nullable=True)
    module_file_name: str = Field(nullable=False)
    function_name: str = Field(nullable=False)
    args: dict[str, Any] | None = Field(
        nullable=True, sa_type=JSON, default=None
    )
    description: str = Field(nullable=False, default="")
    is_active: bool = Field(nullable=False, default=True)
    """venv_path is the absolute path to the virtual environment for the interface."""
    venv_path: str | None = Field(nullable=True, default=None)
    installed: bool = Field(nullable=False, default=False)


class InterfaceDb(InterfaceInsert, table=True):
    __tablename__ = "interface"
    id: int = Field(default=None, primary_key=True, index=True)
    interface_group: InterfaceGroup | None = Relationship(
        back_populates="interfaces"
    )
