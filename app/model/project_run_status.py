from pydantic import BaseModel

from app.db.models.task import TaskStatusEnum


class ProjectRunStatus(BaseModel):
    # is used to indicate that the calculation of tiles is not done
    # and no valid numbers of steps can be given until that step is finished
    calculating: bool = False
    message: str
    status: TaskStatusEnum
    finished_tasks: int
    total_tasks: int

    # extended status information, only for Running status
    current_task_name: str = ""
    total_finished_step: int = 0
    total_steps: int = 0
