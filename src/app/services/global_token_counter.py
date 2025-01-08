"""Global token counting module for managing token counts across multiple blocks."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

from src.app.services.error_notification import ErrorNotificationService, ErrorSeverity

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class TokenCounterError(Exception):
    """Base exception for token counter errors."""


class BlockNotFoundError(TokenCounterError):
    """Raised when a block is not found."""


class InvalidTokenCountError(TokenCounterError):
    """Raised when token count is invalid."""


@dataclass
class TokenBlock:
    """Represents a block of content with its token count."""

    id: str
    token_count: int = 0

    def __post_init__(self):
        """Validate token count after initialization."""
        if self.token_count < 0:
            raise InvalidTokenCountError("Token count cannot be negative")


class GlobalTokenCounter:
    """Manages global token counting across multiple blocks with real-time updates."""

    def __init__(self):
        """Initialize the global token counter."""
        self._blocks: dict[str, TokenBlock] = {}
        self._total_tokens: int = 0
        self._listeners: WeakKeyDictionary[Callable[[int], None], None] = (
            WeakKeyDictionary()
        )
        self._lock = asyncio.Lock()
        self._batch_updates: dict[str, int] = {}
        self._batch_update_event = asyncio.Event()
        self._batch_update_task: asyncio.Task | None = None
        self._error_service = ErrorNotificationService()

    @property
    def total_tokens(self) -> int:
        """Get the current total token count."""
        return self._total_tokens

    def add_listener(self, callback: Callable[[int], None]) -> None:
        """Add a listener for token count updates.

        Args:
            callback: Function to call with updated token count

        Raises:
            TypeError: If callback is not callable
        """
        if not callable(callback):
            error = TypeError("Callback must be callable")
            asyncio.create_task(
                self._error_service.notify(
                    message="Invalid callback provided for token counter listener",
                    severity=ErrorSeverity.ERROR,
                    source="GlobalTokenCounter",
                    details={"callback_type": str(type(callback))},
                    error_code="INVALID_CALLBACK",
                )
            )
            raise error
        self._listeners[callback] = None

    async def update_block(self, block_id: str, token_count: int) -> None:
        """Update token count for a block.

        Args:
            block_id: ID of the block to update
            token_count: New token count for the block

        Raises:
            InvalidTokenCountError: If token count is invalid
        """
        try:
            if token_count < 0:
                raise InvalidTokenCountError("Token count cannot be negative")

            async with self._lock:
                old_count = (
                    self._blocks[block_id].token_count
                    if block_id in self._blocks
                    else 0
                )

                # If token count is 0, remove the block
                if token_count == 0:
                    if block_id in self._blocks:
                        del self._blocks[block_id]
                else:
                    self._blocks[block_id] = TokenBlock(
                        id=block_id, token_count=token_count
                    )

                # Recalculate total tokens
                self._total_tokens = sum(
                    block.token_count for block in self._blocks.values()
                )
                await self._notify_listeners()

        except InvalidTokenCountError as e:
            await self._error_service.notify(
                message=str(e),
                severity=ErrorSeverity.ERROR,
                source="GlobalTokenCounter",
                details={"block_id": block_id, "token_count": token_count},
                error_code="INVALID_TOKEN_COUNT",
            )
            raise
        except Exception as e:
            await self._error_service.notify(
                message=f"Failed to update block tokens: {e!s}",
                severity=ErrorSeverity.ERROR,
                source="GlobalTokenCounter",
                details={
                    "block_id": block_id,
                    "token_count": token_count,
                    "error_type": type(e).__name__,
                },
                error_code="UPDATE_BLOCK_ERROR",
            )
            raise

    async def update_blocks_batch(self, updates: dict[str, int]) -> None:
        """Update multiple blocks at once efficiently."""
        if not updates:
            logger.debug("Skipping batch update - no updates provided")
            return

        try:
            # Validate all token counts first
            invalid_updates = {
                block_id: count
                for block_id, count in updates.items()
                if not isinstance(count, int) or count < 0
            }
            if invalid_updates:
                raise ValueError(
                    f"Invalid token counts in batch update: {invalid_updates}"
                )

            async with self._lock:
                # Process all updates within a single lock
                for block_id, count in updates.items():
                    if block_id not in self._blocks:
                        self._blocks[block_id] = TokenBlock(id=block_id, token_count=0)
                    self._blocks[block_id].token_count = count
                self._total_tokens = sum(
                    block.token_count for block in self._blocks.values()
                )

            logger.debug(
                f"Batch updated {len(updates)} blocks. New total: {self._total_tokens}"
            )

        except Exception as e:
            logger.error(f"Error in batch update: {e!s}")
            raise

    async def remove_block(self, block_id: str) -> None:
        """Remove a block from token counting.

        Args:
            block_id: ID of block to remove

        Raises:
            BlockNotFoundError: If block does not exist
        """
        try:
            async with self._lock:
                if block_id not in self._blocks:
                    raise BlockNotFoundError(f"Block {block_id} not found")

                self._total_tokens -= self._blocks[block_id].token_count
                del self._blocks[block_id]
                await self._notify_listeners()

        except BlockNotFoundError as e:
            await self._error_service.notify(
                message=str(e),
                severity=ErrorSeverity.WARNING,
                source="GlobalTokenCounter",
                details={"block_id": block_id},
                error_code="BLOCK_NOT_FOUND",
            )
            raise
        except Exception as e:
            await self._error_service.notify(
                message=f"Failed to remove block: {e!s}",
                severity=ErrorSeverity.ERROR,
                source="GlobalTokenCounter",
                details={"block_id": block_id, "error_type": type(e).__name__},
                error_code="REMOVE_BLOCK_ERROR",
            )
            raise

    async def set_total_tokens(self, total_tokens: int) -> None:
        """Set the total token count directly.

        Args:
            total_tokens: New total token count

        Raises:
            InvalidTokenCountError: If token count is invalid
        """
        try:
            if total_tokens < 0:
                raise InvalidTokenCountError("Total token count cannot be negative")

            async with self._lock:
                old_total = self._total_tokens
                self._total_tokens = total_tokens
                for callback in list(self._listeners.keys()):
                    try:
                        callback(total_tokens)
                    except Exception as e:
                        logger.error(f"Error in token count listener: {e!s}")
                        await self._error_service.notify(
                            message="Error in token count listener",
                            severity=ErrorSeverity.WARNING,
                            source="GlobalTokenCounter",
                            details={"error": str(e)},
                            error_code="LISTENER_ERROR",
                        )

                logger.debug(f"Total tokens updated: {old_total} -> {total_tokens}")

        except Exception as e:
            logger.error(f"Error setting total tokens: {e!s}")
            await self._error_service.notify(
                message="Failed to set total token count",
                severity=ErrorSeverity.ERROR,
                source="GlobalTokenCounter",
                details={"error": str(e)},
                error_code="SET_TOTAL_ERROR",
            )
            raise

    def reset(self) -> None:
        """Reset all token counts and clear all blocks."""
        self._blocks.clear()
        self._total_tokens = 0
        self._batch_updates.clear()
        if self._batch_update_task:
            self._batch_update_task.cancel()
        self._batch_update_task = None

        # Notify listeners synchronously to avoid event loop issues
        for listener in self._listeners:
            try:
                listener(0)
            except Exception as e:
                logger.error(f"Failed to notify listener of reset: {e!s}")

    async def _notify_listeners(self) -> None:
        """Notify all listeners of the current total."""
        invalid_listeners = []

        for callback in self._listeners:
            if not callable(callback):
                await self._error_service.notify(
                    message="Non-callable listener found",
                    severity=ErrorSeverity.WARNING,
                    source="GlobalTokenCounter",
                    details={"callback_type": type(callback).__name__},
                    error_code="INVALID_LISTENER",
                )
                invalid_listeners.append(callback)
                continue

            try:
                callback(self._total_tokens)
            except Exception as e:
                await self._error_service.notify(
                    message="Error in token count listener callback",
                    severity=ErrorSeverity.ERROR,
                    source="GlobalTokenCounter",
                    details={"callback_type": type(callback).__name__, "error": str(e)},
                    error_code="LISTENER_CALLBACK_ERROR",
                )

        # Remove invalid listeners
        for listener in invalid_listeners:
            self._listeners.pop(listener, None)

    def get_block_count(self, block_id: str) -> int:
        """Get token count for a specific block.

        Args:
            block_id: ID of the block

        Returns:
            Token count for the block, or 0 if block not found
        """
        try:
            return self._blocks[block_id].token_count if block_id in self._blocks else 0
        except Exception as e:
            asyncio.create_task(
                self._error_service.notify(
                    message=f"Error retrieving block count: {e!s}",
                    severity=ErrorSeverity.ERROR,
                    source="GlobalTokenCounter",
                    details={"block_id": block_id, "error_type": type(e).__name__},
                    error_code="GET_BLOCK_COUNT_ERROR",
                )
            )
            return 0
