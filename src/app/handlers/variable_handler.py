"""Variable content handler module."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from src.app.utils.exceptions import ReferenceError

from .reference_handler import ReferenceHandler

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class VariableHandler(ReferenceHandler):
    """Handler for variable content."""

    def __init__(self):
        """Initialize variable handler."""
        super().__init__()

    async def get_content(self, content: Any) -> AsyncGenerator[str, None]:
        """Get content from variable.

        Args:
            content: Variable content or dict with 'value' key

        Yields:
            Content as string

        Raises:
            ReferenceError: If content cannot be converted to string
        """

        if isinstance(content, dict):
            content = content.get("value")

        if content is None:
            msg = "Missing variable content"
            raise ReferenceError(msg)

        try:
            if isinstance(content, bytes | bytearray):
                yield content.decode("utf-8")
            else:
                yield str(content)
        except Exception as e:
            msg = f"Failed to convert variable content to string: {e!s}"
            raise ReferenceError(msg) from e

    def get_cache_key(self, reference: dict[str, Any]) -> str:
        """Get cache key based on variable name and content hash.

        Args:
            reference: Reference configuration with variable details

        Returns:
            Cache key string

        Raises:
            ReferenceError: If variable content is invalid
        """
        name = reference.get("name")
        value = reference.get("value")

        if not name or value is None:
            msg = "Missing variable name or value"
            raise ReferenceError(msg)

        content_hash = hashlib.sha256(str(value).encode()).hexdigest()
        return f"var:{name}:{content_hash}"

    def should_recount(
        self, reference: dict[str, Any], cached_info: dict[str, Any] | None = None
    ) -> bool:
        """Check if variable value has changed.

        Args:
            reference: Reference configuration with variable details
            cached_info: Previously cached counting info

        Returns:
            True if variable value has changed

        Raises:
            ReferenceError: If variable content is invalid
        """
        if not cached_info:
            return True

        current_value = reference.get("value")
        if current_value is None:
            msg = f"Missing value for variable {reference.get('name')}"
            raise ReferenceError(msg)

        current_hash = hashlib.sha256(str(current_value).encode()).hexdigest()
        cached_hash = cached_info.get("content_hash")

        return current_hash != cached_hash
