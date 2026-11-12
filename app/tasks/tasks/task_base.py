from app.db.models.task import TaskDb
from app.repository.task_repository import TaskRepository


def get_previous_task(task: TaskDb, task_repository: TaskRepository, previous_task_id: int) -> TaskDb:
    if previous_task_id > 0:
        return task_repository.get_by_id(previous_task_id)

    # else
    run_tasks = task_repository.get_by_run_id(task.project_run_id)
    return next((s for s in run_tasks
                 if s.task_type.order == (task.task_type.order-1) and
                 (s.interface_id is None or s.interface_id == task.interface_id)), None
                )
