import asyncio
import logging

logger = logging.getLogger(__name__)


def fire_task(coro, label: str = "") -> asyncio.Task:
    """Schedule a coroutine as a background task and log any exception it raises."""
    task = asyncio.create_task(coro)

    def _on_done(t: asyncio.Task) -> None:
        if not t.cancelled() and t.exception():
            logger.error(f"Background task failed [{label}]: {t.exception()}")

    task.add_done_callback(_on_done)
    return task
