"""Base API handler for external service integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.app.models.api_endpoint import APIEndpoint


class APIHandler(ABC):
    """Abstract base class for API handlers."""

    def __init__(self, endpoint: APIEndpoint):
        """Initialize with API endpoint configuration."""
        self.endpoint = endpoint
        self.base_url = endpoint.base_url.rstrip("/")
        self.headers = endpoint.headers or {}
        if endpoint.auth_type == "bearer" and endpoint.auth_token:
            self.headers["Authorization"] = f"Bearer {endpoint.auth_token}"

    @abstractmethod
    async def get_resource(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Get a resource from the API.

        Args:
            path: Resource path (will be appended to base_url)
            params: Optional query parameters

        Returns:
            Parsed response data

        Raises:
            APIError: If request fails or response is invalid
        """

    @abstractmethod
    async def validate_configuration(self) -> bool:
        """Validate the API configuration is correct and accessible.

        Returns:
            True if configuration is valid

        Raises:
            APIError: If configuration is invalid
        """

    @abstractmethod
    def get_rate_limit(self) -> int | None:
        """Get current rate limit if available.

        Returns:
            Current rate limit or None if not supported
        """
