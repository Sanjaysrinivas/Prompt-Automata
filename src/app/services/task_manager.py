"""Task manager for token counting operations."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from ..handlers.handler_factory import ReferenceHandlerFactory
from ..utils.exceptions import TaskError
from .background_processor import BackgroundProcessor, TaskPriority, TaskStatus
from .token_service import TokenCountingService

logger = logging.getLogger(__name__)


class TokenCountingTaskManager:
    """Manager for token counting tasks."""

    def __init__(
        self,
        token_service: TokenCountingService,
        background_processor: BackgroundProcessor,
    ):
        """Initialize task manager.

        Args:
            token_service: Token counting service
            background_processor: Background processor for tasks
        """
        self.token_service = token_service
        self.processor = background_processor
        self.handler_factory = ReferenceHandlerFactory()

    async def count_tokens_async(
        self,
        references: list[dict[str, Any]],
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> UUID:
        """Submit token counting task for multiple references.

        Args:
            references: List of references to count tokens for
            priority: Task priority level

        Returns:
            Task ID
        """
        return await self.processor.submit(
            self._count_tokens_batch,
            references,
            priority=priority,
        )

    async def get_task_status(self, task_id: UUID) -> dict[str, Any]:
        """Get status of a token counting task.

        Args:
            task_id: Task ID

        Returns:
            Task status information
        """
        task = self.processor.get_task(task_id)
        if not task:
            return {
                "status": TaskStatus.FAILED.value,
                "error": "Task not found",
            }

        status = {
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat()
            if task.completed_at
            else None,
        }

        if task.status == TaskStatus.COMPLETED:
            status["result"] = task.result
        elif task.status == TaskStatus.FAILED:
            status["error"] = str(task.error)

        return status

    async def _count_tokens_batch(
        self,
        references: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Count tokens for multiple references.

        Args:
            references: List of references to count tokens for

        Returns:
            Dictionary with token counts and metadata

        Raises:
            TaskError: If token counting fails
        """
        try:
            results = []
            total_tokens = 0
            errors = []

            for ref in references:
                try:
                    if ref["type"] == "variable":
                        content = ref["value"]
                        count, metadata = await self.token_service.count_tokens(
                            content,
                            use_cache=True,
                        )
                    else:
                        handler = self.handler_factory.get_handler(ref)
                        (
                            count,
                            metadata,
                        ) = await self.token_service.count_tokens_from_reference(
                            ref,
                            handler,
                            use_cache=True,
                        )

                    results.append(
                        {
                            "reference": ref,
                            "token_count": count,
                            "metadata": metadata,
                        }
                    )
                    total_tokens += count
                except Exception as e:
                    errors.append(
                        {
                            "reference": ref,
                            "error": str(e),
                        }
                    )

            return {
                "total_tokens": total_tokens,
                "results": results,
                "errors": errors,
            }
        except Exception as e:
            msg = f"Batch token counting failed: {e!s}"
            raise TaskError(msg) from e
