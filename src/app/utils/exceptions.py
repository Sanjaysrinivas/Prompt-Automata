"""Custom exceptions and error handling utilities."""

from __future__ import annotations

from werkzeug.exceptions import BadRequest


class TokenizationError(Exception):
    """Raised when token counting or encoding operations fail."""


class ReferenceError(Exception):
    """Raised when reference content cannot be accessed or processed."""


class RefreshError(Exception):
    """Raised when refresh operations fail."""


class TaskError(Exception):
    """Exception raised when a background task fails."""


def raise_bad_request(message: str, error: str | Exception | None = None) -> None:
    """Raise a BadRequest exception with the given message and optional error details.

    Args:
        message: The error message to display
        error: Optional error details or exception

    Raises:
        BadRequest: Always raises this exception with the formatted message
    """
    if error:
        error_msg = str(error) if isinstance(error, Exception) else error
        message = f"{message}: {error_msg}"

    raise BadRequest(message)
