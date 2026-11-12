import enum
from typing import Any, List
from datetime import datetime
from uuid import UUID
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import JSON, Column, Enum


class TaskStatusEnum(enum.Enum):
    PENDING = 0
    QUEUED = 1
    RUNNING = 2
    FINISHED = 3
    ERROR = 4
    KILLED = 5

    @classmethod
    def has_member_key(self, key):
        return key in self.__members__


# Run Type


class RunType(SQLModel, table=True):
    __tablename__ = "run_type"
    id: int | None = Field(default=None, primary_key=True, index=True)
    name: str = Field(nullable=False)
    tasks: List["TaskType"] = Relationship(back_populates="run_type")


# Task Type


class TaskType(SQLModel, table=True):
    __tablename__ = "task_type"
    id: int | None = Field(default=None, primary_key=True, index=True)
    name: str = Field(nullable=False)
    run_type_id: int = Field(nullable=False, foreign_key="run_type.id")
    order: int = Field(nullable=False)
    is_interface_dependent: bool = Field(nullable=False)
    run_type: RunType | None = Relationship(back_populates="tasks")
    tasks: List["TaskDb"] = Relationship(back_populates="task_type")


# Task


class TaskInsert(SQLModel):
    project_run_id: int | None = Field(
        nullable=False, foreign_key="project_run.id"
    )
    task_type_id: int | None = Field(nullable=False, foreign_key="task_type.id")
    interface_id: int | None = Field(nullable=True, foreign_key="interface.id")
    attributes: dict[str, Any] | None = Field(nullable=True, sa_type=JSON)
    input_path: str | None = Field(nullable=True, default=None)
    status: TaskStatusEnum = Field(
        sa_column=Column(
            Enum(TaskStatusEnum), nullable=False, default=TaskStatusEnum.PENDING
        ),
    )


class TaskDb(TaskInsert, table=True):
    __tablename__ = "task"
    id: int | None = Field(default=None, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime = Field(default_factory=datetime.now)
    task_type: TaskType = Relationship(back_populates="tasks")
    steps: List["TaskStepDb"] = Relationship(back_populates="task", cascade_delete=True)


# Task Step


class TaskStepInsert(SQLModel):
    task_id: int | None = Field(nullable=False, foreign_key="task.id")
    task_type_id: int | None = Field(nullable=False)
    interface_id: int | None = Field(nullable=True)
    input_path: str | None = Field(nullable=True, default=None)
    external_id: UUID = Field(index=True, nullable=False)
    status: TaskStatusEnum = Field(
        sa_column=Column(
            Enum(TaskStatusEnum), nullable=False, default=TaskStatusEnum.PENDING
        ),
    )


class TaskStepDb(TaskStepInsert, table=True):
    __tablename__ = "task_step"
    id: int | None = Field(default=None, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime | None = Field(nullable=True, default=None)
    output_path: str | None = Field(nullable=True, default=None)
    pid: int | None = Field(nullable=True, default=None)
    started_at: datetime | None = Field(nullable=True, default=None)
    result: List["TaskStepResultDb"] = Relationship(back_populates="task_step", cascade_delete=True)
    task: TaskDb = Relationship(back_populates="steps")


# Task Step Result


class TaskStepResultInsert(SQLModel):
    task_step_id: int | None = Field(
        nullable=True, foreign_key="task_step.id", default=None
    )
    success: bool = Field(default=False)
    error: dict[str, Any] | None = Field(nullable=True, sa_type=JSON)
    additional_info: dict[str, Any] | None = Field(nullable=True, sa_type=JSON)


class TaskStepResultDb(TaskStepResultInsert, table=True):
    __tablename__ = "task_step_result"
    id: int | None = Field(default=None, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    task_step: TaskStepDb = Relationship(back_populates="result")
