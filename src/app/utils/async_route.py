"""Utility for handling async routes in Flask."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import current_app


def async_route(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle async route handlers.

    Args:
        f: The async route handler function

    Returns:
        Wrapped function that runs in the event loop
    """

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(f(*args, **kwargs))
            return result
        except Exception as e:
            current_app.logger.exception(f"Error in async route: {e!s}")
            raise

    return wrapper
