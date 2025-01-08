"""Token counting service module."""

from __future__ import annotations

import logging
from typing import Any

from litellm import token_counter

from src.app.utils.exceptions import TokenizationError

logger = logging.getLogger(__name__)


class TokenCountingService:
    """Service for counting tokens in content."""

    def __init__(self):
        """Initialize token counting service."""

    async def count_tokens(
        self,
        content: str,
        use_cache: bool = True,
    ) -> tuple[int, dict[str, Any]]:
        """Count tokens in content."""
        if not content:
            return 0, {"cache_hit": False}

        try:
            count = self._count_tokens(content)
            return count, {"cache_hit": False}
        except Exception as e:
            logger.exception(f"Token counting failed: {e!s}")
            msg = f"Failed to count tokens: {e!s}"
            raise TokenizationError(msg)

    def _count_tokens(self, content: str) -> int:
        """Count tokens in content without caching."""
        try:
            return token_counter(model="gpt-3.5-turbo", text=content)
        except Exception as e:
            logger.exception(f"Tokenization failed: {e!s}")
            msg = f"Failed to tokenize content: {e!s}"
            raise TokenizationError(msg)
