"""Background processing system for token counting tasks."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from ..utils.exceptions import TaskError
from ..utils.retry import retry

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""

    HIGH = 0
    MEDIUM = 1
    LOW = 2


class TaskStatus(Enum):
    """Task status states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Background task representation."""

    id: UUID
    func: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority
    status: TaskStatus
    result: Any | None = None
    error: Exception | None = None
    created_at: datetime = datetime.utcnow()
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retries: int = 0
    max_retries: int = 3


class BackgroundProcessor:
    """Processor for background tasks with priority queue."""

    def __init__(self, max_workers: int = 5):
        """Initialize background processor.

        Args:
            max_workers: Maximum number of concurrent worker tasks
        """
        self.max_workers = max_workers
        self.tasks: dict[UUID, Task] = {}
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.workers: list[asyncio.Task] = []
        self._running = False

    async def start(self):
        """Start the background processor."""
        if self._running:
            return

        self._running = True
        self.workers = [
            asyncio.create_task(self._worker()) for _ in range(self.max_workers)
        ]

    async def stop(self):
        """Stop the background processor."""
        self._running = False
        await self.queue.join()
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)

    async def submit(
        self,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.MEDIUM,
        **kwargs,
    ) -> UUID:
        """Submit a task for background processing.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            priority: Task priority level
            **kwargs: Keyword arguments for func

        Returns:
            Task ID
        """
        task_id = uuid4()
        task = Task(
            id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            status=TaskStatus.PENDING,
        )
        self.tasks[task_id] = task
        await self.queue.put((priority.value, task))
        return task_id

    def get_task(self, task_id: UUID) -> Task | None:
        """Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        return self.tasks.get(task_id)

    @retry(retries=3, delay=1.0, backoff=2.0)
    async def _execute_task(self, task: Task) -> Any:
        """Execute a task with retry logic.

        Args:
            task: Task to execute

        Returns:
            Task result

        Raises:
            TaskError: If task execution fails
        """
        task.retries += 1
        try:
            if asyncio.iscoroutinefunction(task.func):
                return await task.func(*task.args, **task.kwargs)
            return task.func(*task.args, **task.kwargs)
        except Exception as e:
            if task.retries >= task.max_retries:
                msg = f"Task {task.id} failed after {task.retries} retries: {e!s}"
                raise TaskError(msg) from e
            raise

    async def _worker(self):
        """Worker coroutine for processing tasks."""
        while self._running:
            try:
                _, task = await self.queue.get()
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()

                try:
                    while task.retries < task.max_retries:
                        try:
                            if asyncio.iscoroutinefunction(task.func):
                                task.result = await task.func(*task.args, **task.kwargs)
                            else:
                                task.result = task.func(*task.args, **task.kwargs)
                            task.status = TaskStatus.COMPLETED
                            break
                        except Exception as e:
                            task.retries += 1
                            if task.retries >= task.max_retries:
                                raise
                            logger.warning(
                                f"Task {task.id} failed (attempt {task.retries}): {e!s}"
                            )
                            await asyncio.sleep(2.0 ** (task.retries - 1))
                    else:
                        raise Exception("Max retries exceeded")
                except Exception as e:
                    task.error = e
                    task.status = TaskStatus.FAILED
                    logger.error(f"Task {task.id} failed: {e!s}")
                finally:
                    task.completed_at = datetime.utcnow()
                    self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e!s}")
