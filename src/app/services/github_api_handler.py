"""GitHub API handler implementation."""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from typing import Any

import httpx
from flask import session

from src.app import db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.app.models.api_endpoint import APIEndpoint
from src.app.models.api_token import APIToken
from src.app.models.reference_models import ReferenceType
from src.app.services.api_handler import APIHandler
from src.app.services.reference_handlers import ReferenceResolutionResult


class GitHubAPIHandler(APIHandler):
    """Handler for GitHub API references."""

    def __init__(self, endpoint: APIEndpoint):
        """Initialize the GitHub API handler.

        Args:
            endpoint: The GitHub API endpoint configuration
        """
        self.endpoint = endpoint
        self.base_url = endpoint.base_url.rstrip("/")

        # Get token from session
        self.token = session.get("github_token")

        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    async def _make_request(self, method, endpoint, **kwargs):
        """Make a request to the GitHub API."""
        async with httpx.AsyncClient() as client:
            # Construct API URL
            api_url = f"https://api.github.com{endpoint}"
            logger.debug(f"Making GitHub API request to: {api_url}")

            response = await client.request(
                method, api_url, headers=self.headers, **kwargs
            )

            logger.debug(f"GitHub API response status: {response.status_code}")
            if response.status_code >= 400:
                error_data = response.json()
                logger.error(f"GitHub API error: {json.dumps(error_data)}")
                raise ValueError(
                    f"GitHub API error ({response.status_code}): {json.dumps(error_data)}"
                )

            return response.json()

    @property
    def reference_type(self) -> ReferenceType:
        return ReferenceType.API

    async def get_resource(
        self, path: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Get a resource from the GitHub API."""
        return await self._make_request("GET", path, params=params)

    async def validate_configuration(self) -> bool:
        """Validate the GitHub API configuration."""
        try:
            # Try to access /rate_limit endpoint which is available to all users
            await self.get_resource("/rate_limit")
            return True
        except Exception as e:
            raise ValueError(f"Invalid GitHub configuration: {e!s}")

    def get_rate_limit(self) -> int | None:
        """Get current GitHub API rate limit."""
        try:
            rate_data = self.get_resource("/rate_limit")
            return rate_data["resources"]["core"]["remaining"]
        except Exception:
            return None

    async def get_issue_content(
        self, owner: str, repo: str, issue_number: str
    ) -> dict[str, Any]:
        """Get content of a specific GitHub issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            Dictionary containing issue data including content
        """
        try:
            # Make request to GitHub API issues endpoint
            issue_data = await self._make_request(
                "GET", f"/repos/{owner}/{repo}/issues/{issue_number}"
            )

            return {
                "title": issue_data.get("title"),
                "number": issue_data.get("number"),
                "state": issue_data.get("state"),
                "created_at": issue_data.get("created_at"),
                "updated_at": issue_data.get("updated_at"),
                "body": issue_data.get("body", ""),
            }
        except Exception as e:
            logger.error(f"Error fetching issue content: {e!s}")
            return None

    async def validate(self, reference_value: str) -> tuple[bool, str | None]:
        """Validate GitHub API reference format."""
        try:
            # Expected format: owner/repo/path
            parts = reference_value.split("/")
            if len(parts) < 2:
                return (
                    False,
                    "Invalid GitHub reference format. Expected: owner/repo/[path]",
                )
            return True, None
        except Exception as e:
            return False, f"Validation error: {e!s}"

    async def parse_response(self, response: httpx.Response) -> str:
        """Parse GitHub API response."""
        try:
            data = response.json()

            # For file contents, GitHub returns Base64 encoded content
            if isinstance(data, dict):
                if "content" in data:
                    # Decode Base64 content
                    content = data["content"].replace(
                        "\n", ""
                    )  # Remove newlines that GitHub adds
                    return base64.b64decode(content).decode("utf-8")
                return json.dumps(data, indent=2)
            if isinstance(data, list):
                return json.dumps(data, indent=2)
            return str(data)
        except Exception as e:
            logger.error(f"Error parsing GitHub response: {e!s}")
            return str(response.text)

    async def get_issue(self, issue_number: str) -> ReferenceResolutionResult:
        """Get a GitHub issue by number."""
        try:
            logger.info(f"Looking up GitHub issue: {issue_number}")
            response = await self._make_request("GET", f"/issues/{issue_number}")

            # Extract relevant issue information
            title = response.get("title", "")
            body = response.get("body", "")
            content = f"Issue #{issue_number}: {title}\n\n{body}"

            return ReferenceResolutionResult(content=content, metadata=response)
        except Exception as e:
            logger.error(f"Error fetching issue #{issue_number}: {e!s}")
            raise ValueError(f"Failed to fetch issue: {e!s}")

    async def resolve(self, reference_value: str) -> ReferenceResolutionResult:
        """Resolve GitHub API reference."""
        try:
            is_valid, error = await self.validate(reference_value)
            if not is_valid:
                return ReferenceResolutionResult(success=False, error=error)

            url, params = self._build_api_url(reference_value)
            print(
                f"Requesting URL: {url}" + (f" with params: {params}" if params else "")
            )

            async with httpx.AsyncClient() as client:
                if params:
                    response = await client.get(
                        url, params=params, headers=self.headers, timeout=10
                    )
                else:
                    response = await client.get(url, headers=self.headers, timeout=10)

                print(f"Response status code: {response.status_code}")

                if response.status_code == 200:
                    parsed_response = await self.parse_response(response)
                    return ReferenceResolutionResult(
                        success=True, value=parsed_response
                    )
                error_data = response.json()
                error_message = error_data.get("message", "Unknown error")
                documentation_url = error_data.get("documentation_url", "")
                full_error = (
                    f"GitHub API error ({response.status_code}): {error_message}"
                )
                if documentation_url:
                    full_error += f"\nFor more information, see: {documentation_url}"
                print(f"Error response: {error_data}")
                return ReferenceResolutionResult(success=False, error=full_error)

        except Exception as e:
            print(f"Exception occurred: {e!s}")
            return ReferenceResolutionResult(
                success=False, error=f"Error processing request: {e!s}"
            )

    async def validate_token(self, token: str) -> tuple[bool, str | None]:
        """Validate a GitHub token.

        Args:
            token: GitHub token to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {token}",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/user", headers=headers, timeout=10.0
                )

                if response.status_code == 200:
                    return True, None
                if response.status_code == 401:
                    return False, "Invalid GitHub token"
                return False, f"GitHub API error: {response.status_code}"

        except httpx.TimeoutException:
            return False, "GitHub API request timed out"
        except Exception as e:
            logger.error(f"Error validating GitHub token: {e!s}")
            return False, f"Error validating token: {e!s}"

    def _get_headers(self) -> dict[str, str]:
        """Get headers for GitHub API requests.

        Returns:
            Dictionary of request headers
        """
        # Refresh token from session
        self.token = session.get("github_token")
        if not self.token:
            raise ValueError("GitHub token not configured")

        self.headers["Authorization"] = f"Bearer {self.token}"
        return self.headers

    async def get_resource(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Get a resource from the GitHub API.

        Args:
            path: API endpoint path
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            httpx.RequestError: If the request fails
            TimeoutError: If the request times out
            ValueError: If the response contains invalid JSON
        """
        url = f'{self.base_url}/{path.lstrip("/")}'
        headers = self._get_headers()

        try:
            logger.debug(f"Making GitHub API request to: {url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, headers=headers, params=params, timeout=10.0
                )

                # Log response status
                logger.debug(f"GitHub API response status: {response.status_code}")

                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error(f"GitHub API error: {e.response.text}")
                    raise ValueError(
                        f"GitHub API error ({e.response.status_code}): {e.response.text}"
                    )

                try:
                    data = response.json()
                except ValueError:
                    logger.error(
                        f"Invalid JSON response from GitHub API: {response.text[:200]}"
                    )
                    raise ValueError("Invalid JSON response from GitHub API")

                # Update token last used time
                if self.token:
                    token = APIToken.query.filter_by(
                        service="github", is_active=True, is_valid=True
                    ).first()
                    if token:
                        token.last_used = datetime.utcnow()
                        try:
                            db.session.commit()
                        except Exception as e:
                            logger.error(f"Error updating token last_used: {e!s}")
                            db.session.rollback()

                return data

        except httpx.TimeoutException:
            logger.error(f"GitHub API request timed out: {url}")
            raise TimeoutError("Request timed out")
        except httpx.RequestError as e:
            logger.error(f"GitHub API request failed: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in GitHub API request: {e!s}")
            raise ValueError(f"Error processing GitHub API request: {e!s}")

    async def get_repository_issues(self, owner: str, repo: str) -> list:
        """Get issues from a GitHub repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of repository issues

        Raises:
            TimeoutError: If the request times out
            ValueError: If the response format is invalid
        """
        try:
            issues = await self.get_resource(f"/repos/{owner}/{repo}/issues")
            return issues
        except Exception as e:
            logger.error(f"Error fetching repository issues: {e!s}")
            raise

    def _build_api_url(self, reference_value: str) -> tuple[str, str | None]:
        """Build GitHub API URL from reference."""
        parts = reference_value.split("/")
        owner = parts[0]
        repo = parts[1]

        if len(parts) <= 2:
            # Return repository info URL if no path specified
            return f"https://api.github.com/repos/{owner}/{repo}", None

        # Handle special endpoints
        if parts[2] == "issues":
            return f"https://api.github.com/repos/{owner}/{repo}/issues", None
        if parts[2] == "search":
            if len(parts) < 4:
                raise ValueError("Search query required")
            query = "/".join(parts[3:])
            return "https://api.github.com/search/repositories", f"q={query}"

        # Default to contents API
        path = "/".join(parts[2:])
        return f"https://api.github.com/repos/{owner}/{repo}/contents/{path}", None
