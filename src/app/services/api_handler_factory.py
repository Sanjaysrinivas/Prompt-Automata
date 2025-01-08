"""Factory for creating API handlers."""

from __future__ import annotations

from src.app.models.api_endpoint import APIEndpoint
from src.app.services.api_handler import APIHandler
from src.app.services.github_api_handler import GitHubAPIHandler


class APIHandlerFactory:
    """Factory for creating API handlers based on endpoint type."""

    _handlers: dict[str, type[APIHandler]] = {
        "github": GitHubAPIHandler,
        # Add more handlers here as they are implemented
    }

    @classmethod
    def create_handler(cls, endpoint: APIEndpoint) -> APIHandler:
        """Create an API handler for the given endpoint.

        Args:
            endpoint: API endpoint configuration

        Returns:
            Appropriate API handler instance

        Raises:
            ValueError: If no handler exists for endpoint type
        """
        handler_class = cls._handlers.get(endpoint.type.lower())
        if not handler_class:
            raise ValueError(f"No handler available for API type: {endpoint.type}")

        return handler_class(endpoint)
