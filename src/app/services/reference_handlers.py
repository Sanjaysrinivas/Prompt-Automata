"""Core abstractions for handling different types of references."""

from __future__ import annotations

import abc
import logging
from collections.abc import Coroutine
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol
from urllib.parse import urljoin

import httpx

from src.app.models.api_endpoint import APIEndpoint
from src.app.models.reference_models import AllowedDirectory, ReferenceType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReferenceError(Exception):
    """Base exception for reference handling errors."""


class ValidationError(ReferenceError):
    """Raised when reference validation fails."""


class ResolutionError(ReferenceError):
    """Raised when reference resolution fails."""


class AuthenticationError(ReferenceError):
    """Raised when API authentication fails."""


class RateLimitError(ReferenceError):
    """Raised when API rate limit is exceeded."""


@dataclass
class ReferenceResolutionResult:
    """Result of resolving a reference."""

    success: bool
    value: str | None = None
    error: str | None = None


class ReferenceHandler(Protocol):
    """Protocol defining the interface for reference handlers."""

    @property
    def reference_type(self) -> ReferenceType:
        """Get the type of reference this handler manages."""
        ...

    async def resolve(
        self, reference_value: str
    ) -> Coroutine[Any, Any, ReferenceResolutionResult]:
        """Resolve a reference value to its actual content.

        Args:
            reference_value: Value to resolve.

        Returns:
            Resolution result containing success status and value or error.
        """
        ...

    async def validate(
        self, reference_value: str
    ) -> Coroutine[Any, Any, tuple[bool, str | None]]:
        """Validate if a reference value is valid for this handler.

        Args:
            reference_value: Value to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        ...


class FilePathValidator:
    """Validator for file path references."""

    def __init__(self, allowed_directories: list[AllowedDirectory]):
        """Initialize with list of allowed directories."""
        self.allowed_directories = allowed_directories
        logger.info(
            f"Initialized FilePathValidator with {len(allowed_directories)} allowed directories"
        )

    def validate_path(self, path: str) -> tuple[bool, str | None]:
        """
        Validate if a path is allowed based on configured directories.

        Args:
            path: The path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            return AllowedDirectory.is_path_allowed(path)
        except Exception as e:
            logger.error(f"Error validating path {path}: {e!s}")
            return False, f"Path validation error: {e!s}"


@dataclass
class TokenInfo:
    """Information about an authentication token."""

    token: str
    expires_at: datetime | None = None
    refresh_token: str | None = None


class APIHandler(abc.ABC):
    """Base class for API reference handlers."""

    def __init__(self, endpoint: APIEndpoint) -> None:
        """Initialize with API endpoint configuration."""
        self.endpoint = endpoint
        self.base_url = endpoint.base_url
        self.headers = endpoint.headers or {}
        self.rate_limit = endpoint.rate_limit
        self._last_request_time: datetime | None = None
        self._request_count = 0
        self._token_info: TokenInfo | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

        if endpoint.auth_token:
            self._setup_auth(endpoint.auth_type, endpoint.auth_token)

        logger.info("Initialized APIHandler for endpoint: %s", endpoint.name)

    def _setup_auth(self, auth_type: str, auth_token: str) -> None:
        """Set up authentication headers based on auth type.

        Args:
            auth_type: Type of authentication (e.g., 'bearer', 'basic')
            auth_token: Authentication token
        """
        if auth_type.lower() == "bearer":
            self.headers["Authorization"] = f"Bearer {auth_token}"
        elif auth_type.lower() == "basic":
            self.headers["Authorization"] = f"Basic {auth_token}"
        else:
            logger.warning("Unknown auth type: %s", auth_type)

    def _check_rate_limit(self) -> None:
        """Check if we're within rate limits."""
        if not self.rate_limit:
            return

        now = datetime.now()
        if self._last_request_time:
            time_diff = now - self._last_request_time
            if time_diff < timedelta(seconds=1):
                self._request_count += 1
                if self._request_count > self.rate_limit:
                    raise RateLimitError("Rate limit exceeded")
            else:
                self._request_count = 1
        self._last_request_time = now

    async def _refresh_token(self) -> None:
        """Refresh the authentication token if needed."""
        if not self._token_info or not self._token_info.refresh_token:
            return

        if (
            self._token_info.expires_at
            and datetime.now() >= self._token_info.expires_at
        ):
            logger.info("Token refresh required but not implemented")

    async def make_request(
        self, path: str, method: str = "GET", params: dict[str, Any] | None = None
    ) -> Coroutine[Any, Any, ReferenceResolutionResult]:
        """Make an API request.

        Args:
            path: API path to request
            method: HTTP method
            params: Query parameters

        Returns:
            ReferenceResolutionResult containing the response or error
        """
        try:
            await self._refresh_token()
            self._check_rate_limit()

            url = urljoin(self.base_url, path)
            async with self._client as client:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    headers=self.headers,
                )
                response.raise_for_status()
                return ReferenceResolutionResult(
                    success=True,
                    value=await self.parse_response(response),
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ReferenceResolutionResult(
                    success=False,
                    error="Authentication failed",
                )
            if e.response.status_code == 429:
                return ReferenceResolutionResult(
                    success=False,
                    error="Rate limit exceeded",
                )
            return ReferenceResolutionResult(
                success=False,
                error=f"HTTP error {e.response.status_code}",
            )

        except httpx.RequestError as e:
            return ReferenceResolutionResult(
                success=False,
                error=f"Request failed: {e!s}",
            )

        except Exception as e:
            logger.exception("Unexpected error in make_request")
            return ReferenceResolutionResult(
                success=False,
                error=f"Unexpected error: {e!s}",
            )

    @abc.abstractmethod
    async def parse_response(
        self, response: httpx.Response
    ) -> Coroutine[Any, Any, str]:
        """Parse API response into a string value.

        Args:
            response: Raw API response

        Returns:
            Parsed string value
        """
        try:
            return str(response.text)
        except Exception as e:
            logger.exception("Error parsing response")
            raise ValueError(f"Failed to parse response: {e!s}")


class ReferenceManager:
    """Manager for handling different types of references."""

    def __init__(self):
        """Initialize with empty handler registry."""
        self._handlers: dict[ReferenceType, ReferenceHandler] = {}
        logger.info("Initialized ReferenceManager")

    def register_handler(self, handler: ReferenceHandler) -> None:
        """
        Register a handler for a reference type.

        Args:
            handler: Handler instance implementing ReferenceHandler protocol
        """
        try:
            self._handlers[handler.reference_type] = handler
            logger.info(f"Registered handler for type: {handler.reference_type}")
        except Exception as e:
            logger.error(f"Error registering handler: {e!s}")
            raise ValueError(f"Failed to register handler: {e!s}")

    async def resolve_reference(
        self, reference_type: ReferenceType, reference_value: str
    ) -> Coroutine[Any, Any, ReferenceResolutionResult]:
        """
        Resolve a reference using the appropriate handler.

        Args:
            reference_type: Type of reference to resolve
            reference_value: Value to resolve

        Returns:
            ReferenceResolutionResult containing the resolution result
        """
        try:
            handler = self._handlers.get(reference_type)
            if not handler:
                error_msg = (
                    f"No handler registered for reference type: {reference_type}"
                )
                logger.error(error_msg)
                return ReferenceResolutionResult(success=False, error=error_msg)

            # Validate first
            is_valid, error = await handler.validate(reference_value)
            if not is_valid:
                error_msg = error or "Invalid reference value"
                logger.warning(f"Validation failed: {error_msg}")
                return ReferenceResolutionResult(success=False, error=error_msg)

            # Then resolve
            logger.info(f"Resolving reference of type {reference_type}")
            return await handler.resolve(reference_value)

        except ReferenceError as e:
            error_msg = f"Reference error: {e!s}"
            logger.error(error_msg)
            return ReferenceResolutionResult(success=False, error=error_msg)

        except Exception as e:
            error_msg = f"Unexpected error resolving reference: {e!s}"
            logger.error(error_msg)
            return ReferenceResolutionResult(success=False, error=error_msg)
