import asyncio
import logging
import traceback

import app.tasks.steps as step_resolver
from app.container import Container
from app.system_state import system_state

logger = logging.getLogger()


async def poll_queue(
    stop_event: asyncio.Event,
    enabled: bool = False,
):
    while not stop_event.is_set() and enabled:
        system_state.set_poller_running()
        logger.debug("Polling queue...")
        try:
            dispatcher = Container.dispatcher()
            process_handler = Container.process_handler()
            task_definition = dispatcher.check_for_tasks()
            if task_definition is not None:
                # Create a new task and don't await it
                asyncio.create_task(
                    getattr(step_resolver, task_definition.task_type_name)(
                        task_definition.task_step_id
                    )
                )

            process_handler.check_for_long_running_steps()

        except Exception as e:
            logger.error(f"Error polling queue: {e}")
            logger.error(traceback.format_exc())

        # Handle polling interval separately
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=5)
        except asyncio.TimeoutError:
            pass  # Expected timeout for polling interval
