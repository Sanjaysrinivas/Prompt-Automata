"""API response handler module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import aiohttp

from src.app.utils.exceptions import ReferenceError
from src.app.utils.retry import retry

from .reference_handler import ReferenceHandler

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class APIHandler(ReferenceHandler):
    """Handler for API responses."""

    def __init__(self):
        """Initialize API handler."""
        super().__init__()

    @retry(retries=3, delay=1.0, exceptions=(aiohttp.ClientError,))
    async def get_content(self, reference: dict[str, Any]) -> AsyncGenerator[str, None]:
        """Get content from API endpoint.

        Args:
            reference: API reference containing:
                - url: API endpoint URL
                - method: HTTP method (default: GET)
                - headers: Request headers (optional)
                - params: Query parameters (optional)
                - data: Request body (optional)

        Yields:
            Response content in chunks

        Raises:
            ReferenceError: If API request fails
        """
        url = reference.get("url")
        method = reference.get("method", "GET")
        headers = reference.get("headers", {})
        params = reference.get("params", {})
        data = reference.get("data", {})

        if not url:
            msg = "Missing required field 'url' in API reference"
            raise ReferenceError(msg)

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data if method != "GET" else None,
                ) as response,
            ):
                response.raise_for_status()

                async for chunk in response.content.iter_chunked(8192):
                    if chunk:
                        yield chunk.decode("utf-8")
        except aiohttp.ClientError as e:
            msg = f"API request failed: {e!s}"
            raise ReferenceError(msg) from e
