from app.tasks import logger
from app.db.models.task import TaskDb, TaskStatusEnum, TaskStepDb


class TaskValidation:
    @staticmethod
    def check_for_successful_steps(run_tasks: list[TaskDb], task_type_name: str, project_run_id: int) \
            -> (TaskDb, list[TaskStepDb]):
        if run_tasks is None or len(run_tasks) == 0:
            logger.error(f"No tasks found for project run with id: {project_run_id}")
            raise Exception("No tasks found for project run")

        the_task = next((x for x in run_tasks if x.task_type.name == task_type_name), None)
        if the_task is None:
            logger.error(f"No {task_type_name} task found to do the segmentation for run: {project_run_id}")
            raise Exception(f"No {task_type_name} task found to start the segmentation process")

        tiling_step = next((s for s in the_task.steps if s.status == TaskStatusEnum.FINISHED), None)
        if tiling_step is None:
            logger.error(f"No finished steps found for task the {task_type_name} task: {the_task.id}")
            the_task.status = TaskStatusEnum.ERROR
            return the_task, []
            #raise Exception(f"No finished steps found for the {task_type_name} task")

        finished_steps = (s for s in the_task.steps if s.status == TaskStatusEnum.FINISHED)
        steps_with_errors = (s for s in the_task.steps if s.status == TaskStatusEnum.ERROR)

        if steps_with_errors:
            logger.warning(
                f"There are a few steps with errors in the {task_type_name} task: {the_task.id}")

        if finished_steps is None:
            logger.error(
                f"No finished steps found for task the {task_type_name} task: {the_task.id}")
            raise Exception(f"No finished steps found for the {task_type_name} task")

        return the_task, finished_steps


    @staticmethod
    def get_successful_steps(the_task: TaskDb) -> list[TaskStepDb]:

        task_type_name = the_task.task_type.name
        a_finished_step = next((s for s in the_task.steps if s.status == TaskStatusEnum.FINISHED), None)
        if a_finished_step is None:
            logger.error(f"No finished steps found for task the {task_type_name} task: {the_task.id}")
            the_task.status = TaskStatusEnum.ERROR
            return []

        finished_steps = [s for s in the_task.steps if s.status == TaskStatusEnum.FINISHED]
        steps_with_errors = [s for s in the_task.steps if s.status == TaskStatusEnum.ERROR]

        if steps_with_errors:
            logger.warning(
                f"There are a few steps with errors in the {task_type_name} task: {the_task.id}")

        return finished_steps
