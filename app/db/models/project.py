from enum import StrEnum
from typing import Any, List
from datetime import datetime

from sqlalchemy import JSON, Column, Enum
from sqlmodel import SQLModel, Field, Relationship

from app.db.models.task import TaskStatusEnum


class RunTypesEnum(StrEnum):
    SegmentArea = "SegmentArea"
    CompareToBaseImage = "CompareToBaseImage"
    Vectorize = "Vectorize"
    #TODO: this should be removed or have a nicer name
    RunItAll = "RunItAll"

    @classmethod
    def has_member_key(cls, key):
        return key in cls.__members__


class ProjectBase(SQLModel):
    name: str = Field(nullable=False)
    description: str | None = Field(nullable=True, default=None)
    created_by: str = Field(index=True)
    attributes: dict[str, Any] | None = Field(nullable=True, sa_type=JSON)


class Project(ProjectBase, table=True):
    __tablename__ = "project"
    id: int = Field(default=None, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)
    runs: List["ProjectRunDb"] = Relationship(back_populates="project")


# Public models
class ProjectPublicSimple(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool


class ProjectPublic(ProjectPublicSimple):
    runs: List["ProjectRunDb"]


# """ProjectRun Model"""


class ProjectRunInsert(SQLModel):
    name: str = Field(index=True, nullable=False)
    run_type: RunTypesEnum = Field(
        sa_column=Column(
            Enum(RunTypesEnum), nullable=False, default=RunTypesEnum.SegmentArea
        ),
    )
    attributes: dict[str, Any] | None = Field(
        sa_column=Column(JSON), default=None
    )
    project_id: int | None = Field(default=None, foreign_key="project.id")


class ProjectRunDb(ProjectRunInsert, table=True):
    __tablename__ = "project_run"
    id: int | None = Field(default=None, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)
    input_path: str | None = Field(default=None)
    output_path: str | None = Field(nullable=True, default=None)
    # relationships
    project: Project | None = Relationship(back_populates="runs")
