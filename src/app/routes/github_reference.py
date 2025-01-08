"""Routes for GitHub reference handling."""

from __future__ import annotations

import asyncio
import logging
import re

from flask import Blueprint, jsonify, request, session

from src.app.models.api_endpoint import APIEndpoint
from src.app.routes.admin import require_admin
from src.app.services.github_api_handler import GitHubAPIHandler
from src.app.services.token_service import TokenCountingService

# Set up logging
logger = logging.getLogger(__name__)

GITHUB_URL_PARTS = 2  # owner and repo
GITHUB_URL_REGEX = r"^https?://github\.com/[\w-]+/[\w.-]+/?(?:\.git)?$"

github_reference_bp = Blueprint("github_reference", __name__)
token_service = TokenCountingService()


def validate_github_url(url: str) -> tuple[bool, str, list[str]]:
    """Validate GitHub repository URL and extract owner/repo.

    Args:
        url: GitHub repository URL

    Returns:
        Tuple of (is_valid, error_message, [owner, repo] if valid)
    """
    if not url:
        return False, "Repository URL is required", []

    # Check URL format
    if not re.match(GITHUB_URL_REGEX, url):
        return False, "Invalid GitHub repository URL format", []

    try:
        # Extract owner and repo
        parts = url.split("github.com/")[-1].rstrip(".git").rstrip("/").split("/")
        if len(parts) != GITHUB_URL_PARTS:
            return False, "Invalid GitHub repository URL format", []

        owner, repo = parts
        if not owner or not repo:
            return False, "Invalid repository owner or name", []

    except GitHubAPIError as e:
        return False, e.message, []

    return True, "", [owner, repo]


class GitHubAPIError(Exception):
    """Custom exception for GitHub API related errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def _raise_github_error(message: str, status_code: int = 500) -> None:
    """Helper function to raise GitHub API errors with consistent formatting."""
    raise GitHubAPIError(message, status_code)


def _make_response(data=None, error=None, status_code=200):
    """Helper function to format API responses consistently."""
    if error:
        return jsonify(error=error, status_code=status_code)
    return jsonify(data=data, status_code=status_code)


@github_reference_bp.route("/api/github/issues", methods=["GET"])
@require_admin
def get_repository_issues():
    """Get issues from a GitHub repository."""
    try:
        repo_url = request.args.get("repo_url")

        # Validate repository URL
        is_valid, msg, parts = validate_github_url(repo_url)
        if not is_valid:
            logger.warning("Invalid GitHub repository URL")
            return _make_response(error=msg, status_code=400)

        owner, repo = parts
        logger.info("Fetching issues for repository")

        # Get GitHub API endpoint
        endpoint = APIEndpoint.query.filter_by(name="github").first()
        if not endpoint:
            logger.error("GitHub API endpoint not configured")
            _raise_github_error("GitHub API endpoint not configured", 500)

        # Initialize GitHub API handler
        handler = GitHubAPIHandler(endpoint)

        # Check if we have a valid token
        if not handler.token:
            logger.error("No valid GitHub token available")
            _raise_github_error("No valid GitHub token configured", 401)

        # Create an event loop and run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            issues = loop.run_until_complete(handler.get_repository_issues(owner, repo))
        finally:
            loop.close()

        if not isinstance(issues, list):
            logger.error("Invalid response format from GitHub API")
            _raise_github_error("Invalid response format from GitHub API", 500)

        # Format issues for dropdown
        formatted_issues = {
            "repository": f"{owner}/{repo}",
            "issues": [
                {
                    "value": str(issue["number"]),
                    "label": f'#{issue["number"]} - {issue["title"]}',
                    "state": issue["state"],
                    "created_at": issue["created_at"],
                    "updated_at": issue["updated_at"],
                    "html_url": issue["html_url"],
                }
                for issue in issues
                if isinstance(issue, dict)
                and all(
                    k in issue
                    for k in [
                        "number",
                        "title",
                        "state",
                        "created_at",
                        "updated_at",
                        "html_url",
                    ]
                )
            ],
        }

        logger.debug("Formatted issues response")
        logger.info("Successfully fetched")
        return _make_response(data=formatted_issues)

    except TimeoutError:
        logger.exception("Request timed out while fetching issues")
        msg = "Request timed out"
        return _make_response(error=msg, status_code=504)
    except ValueError as e:
        logger.exception("Error in get_repository_issues")
        msg = str(e)
        return _make_response(error=msg, status_code=401 if "token" in msg else 500)
    except Exception as e:
        logger.exception("Error in get_repository_issues")
        msg = str(e)
        return _make_response(error=msg, status_code=500)


@github_reference_bp.route(
    "/api/github/issues/<owner>/<repo>/<issue_number>/content", methods=["GET"]
)
@require_admin
def get_issue_content(owner, repo, issue_number):
    """Get content of a specific GitHub issue."""
    try:
        # Get GitHub API endpoint
        endpoint = APIEndpoint.query.filter_by(name="github").first()
        if not endpoint:
            logger.error("GitHub API endpoint not configured")
            return jsonify({"error": "GitHub API endpoint not configured"}), 500

        # Initialize GitHub API handler
        handler = GitHubAPIHandler(endpoint)

        # Check if we have a valid token
        if "github_token" not in session:
            logger.error("No valid GitHub token available")
            return jsonify({"error": "No valid GitHub token configured"}), 401

        handler.token = session["github_token"]

        try:
            # Create event loop if it doesn't exist
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run async operations in the event loop
            issue = loop.run_until_complete(
                handler.get_issue_content(owner, repo, issue_number)
            )
            if not issue:
                logger.error("Issue not found")
                return jsonify({"error": "Issue not found"}), 404

            # Count tokens for the issue content
            content = issue.get("body", "")
            token_count, _ = (
                loop.run_until_complete(token_service.count_tokens(content))
                if content
                else (0, None)
            )

            return jsonify(
                {
                    "content": content,
                    "title": issue.get("title", ""),
                    "number": issue.get("number"),
                    "state": issue.get("state"),
                    "created_at": issue.get("created_at"),
                    "updated_at": issue.get("updated_at"),
                    "token_count": token_count,
                }
            )

        except Exception as e:
            logger.exception("Error fetching issue content")
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        logger.exception("Error in get_issue_content")
        return jsonify({"error": str(e)}), 500


@github_reference_bp.route("/api/github/validate-token", methods=["POST"])
def validate_token():
    """Validate a GitHub API token."""
    token = request.json.get("token")
    if not token:
        return jsonify({"error": "Token is required"}), 400

    try:
        # Get GitHub API endpoint
        endpoint = APIEndpoint.query.filter_by(name="github").first()
        if not endpoint:
            return jsonify({"error": "GitHub API endpoint not configured"}), 500

        # Initialize GitHub API handler
        handler = GitHubAPIHandler(endpoint)

        # Create event loop if it doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Validate token
        is_valid = loop.run_until_complete(handler.validate_token(token))

        return jsonify({"valid": is_valid})

    except Exception as e:
        logger.exception("Error in validate_token")
        return jsonify({"error": str(e)}), 500
