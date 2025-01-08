"""API response models and utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass
class APIResponse:
    """Standard API response model."""

    success: bool
    data: dict[str, Any] | list[Any] | None = None
    message: str | None = None
    error: str | None = None
    status_code: int = 200

    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary format."""
        response = {"success": self.success}
        if self.data is not None:
            response["data"] = self.data
        if self.message is not None:
            response["message"] = self.message
        if self.error is not None:
            response["error"] = self.error
        return response


class APIResponseBuilder:
    """Builder class for creating standardized API responses."""

    @staticmethod
    def success(
        data: dict[str, Any] | list[Any] | None = None,
        message: str | None = None,
        status_code: int = 200,
    ) -> APIResponse:
        """Create a success response."""
        return APIResponse(
            success=True,
            data=data,
            message=message,
            status_code=status_code,
        )

    @staticmethod
    def error(
        error: str,
        status_code: int = 400,
        data: dict[str, Any] | list[Any] | None = None,
    ) -> APIResponse:
        """Create an error response."""
        return APIResponse(
            success=False,
            error=error,
            data=data,
            status_code=status_code,
        )

    @staticmethod
    def validation_error(message: str, fields: list[str] | None = None) -> APIResponse:
        """Create a validation error response."""
        data = {"fields": fields} if fields else None
        return APIResponse(
            success=False,
            error=message,
            data=data,
            status_code=400,
        )

    @staticmethod
    def not_found(resource: str) -> APIResponse:
        """Create a not found error response."""
        return APIResponse(
            success=False,
            error=f"{resource} not found",
            status_code=404,
        )

    @staticmethod
    def server_error(error: str | None = None) -> APIResponse:
        """Create a server error response."""
        return APIResponse(
            success=False,
            error=error or "Internal server error",
            status_code=500,
        )
