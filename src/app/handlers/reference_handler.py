"""Base reference handler interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class ReferenceHandler(ABC):
    """Base class for reference type handlers."""

    def __init__(self, token_service: Any | None = None):
        """Initialize reference handler.

        Args:
            token_service: Optional token counting service
        """
        self.token_service = token_service

    @abstractmethod
    async def get_content(self, reference: Any) -> AsyncGenerator[str, None]:
        """Get content from reference.

        Args:
            reference: Reference to get content from

        Returns:
            Content from reference

        Raises:
            ReferenceError: If content cannot be retrieved
        """
        raise NotImplementedError

    def _compute_hash(self, content: str) -> str:
        """Compute hash of content.

        Args:
            content: Content to hash

        Returns:
            Hash of content
        """
        return str(hash(content))
