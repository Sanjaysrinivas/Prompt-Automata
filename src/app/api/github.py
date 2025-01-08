from __future__ import annotations

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Define constant for HTTP status code
HTTP_NOT_FOUND = 404


class GitHubAPIHandler:
    """Handler for GitHub API operations."""

    def __init__(self, endpoint):
        """Initialize GitHub API handler.

        Args:
            endpoint: APIEndpoint object containing GitHub API configuration
        """
        self.endpoint = endpoint
        self.base_url = "https://api.github.com"
        self.token = None

    async def _make_request(
        self, method: str, url: str, **kwargs
    ) -> dict[str, Any] | None:
        """Make an HTTP request to the GitHub API.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: API endpoint URL
            **kwargs: Additional arguments to pass to the request

        Returns:
            Response data as dictionary if successful, None otherwise
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.token}",
        }

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.request(method, url, headers=headers, **kwargs) as response,
            ):
                if response.status == HTTP_NOT_FOUND:
                    return None
                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError:
            logger.exception("GitHub API request failed: %s")
            return None

    async def get_issue_content(
        self, owner: str, repo: str, issue_number: str
    ) -> dict[str, Any] | None:
        """Get content of a specific GitHub issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            Issue data as dictionary if successful, None otherwise
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"
        return await self._make_request("GET", url)

    async def get_repository_issues(
        self, owner: str, repo: str
    ) -> list[dict[str, Any]] | None:
        """Get all issues from a GitHub repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of issues if successful, None otherwise
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params = {
            "state": "all",  # Get both open and closed issues
            "sort": "updated",  # Sort by most recently updated
            "direction": "desc",  # Show newest first
            "per_page": 100,  # Maximum number of issues per page
        }
        return await self._make_request("GET", url, params=params)

    async def validate_token(self) -> bool:
        """Validate the GitHub API token.

        Returns:
            True if token is valid, False otherwise
        """
        url = f"{self.base_url}/user"
        result = await self._make_request("GET", url)
        return result is not None
