"""Batch processing module."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..handlers.reference_handler import ReferenceHandler

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Processor for batch processing references."""

    def __init__(self, batch_size: int = 10):
        """Initialize batch processor.

        Args:
            batch_size: Number of references to process in parallel
        """
        self.batch_size = batch_size

    async def process_batch(
        self,
        references: list[Any],
        handler_class: type[ReferenceHandler],
    ) -> None:
        """Process a batch of references in parallel.

        Args:
            references: List of references to process
            handler_class: Reference handler class to use

        Returns:
            None
        """
        tasks = [self._process_reference(ref, handler_class()) for ref in references]
        await asyncio.gather(*tasks)

    async def _process_reference(
        self,
        reference: Any,
        handler: ReferenceHandler,
    ) -> None:
        """Process a single reference.

        Args:
            reference: Reference to process
            handler: Reference handler to use

        Returns:
            None
        """
        try:
            async for _ in handler.get_content(reference):
                pass
        except Exception as e:
            logger.error(f"Failed to process reference: {e!s}")
