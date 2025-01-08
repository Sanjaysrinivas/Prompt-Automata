"""Retry decorator for handling transient failures."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def retry(
    retries: int = 3,
    delay: float = 0.1,
    backoff: float = 2,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    """Retry decorator with exponential backoff.

    Args:
        retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Multiplicative factor for delay between retries
        exceptions: Tuple of exceptions to catch and retry on

    Returns:
        Decorated function that will retry on specified exceptions
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retry_delay = delay
            last_exception = None

            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == retries:
                        logger.error(
                            f"Failed after {retries} retries: {e!s}",
                            exc_info=True,
                        )
                        raise
                    logger.warning(
                        f"Attempt {attempt + 1}/{retries} failed: {e!s}. "
                        f"Retrying in {retry_delay:.2f}s"
                    )
                    time.sleep(retry_delay)
                    retry_delay *= backoff

            if last_exception:
                raise last_exception
            return None

        return wrapper

    return decorator
