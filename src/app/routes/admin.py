"""Admin routes for managing reference system models."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

from aiohttp.client_exceptions import ClientError
from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    session,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from requests.exceptions import RequestException
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import BadRequest, NotFound

from src.app.auth import require_admin
from src.app.models.api_endpoint import APIEndpoint
from src.app.models.db import db
from src.app.models.reference_models import (
    AllowedDirectory,
    APIKey,
    PersistentVariable,
)
from src.app.services.github_api_handler import GitHubAPIHandler

MIN_API_KEY_LENGTH = 16

admin_bp = Blueprint("admin", __name__)

limiter = Limiter(
    key_func=get_remote_address, default_limits=["100 per day", "10 per minute"]
)


@admin_bp.route("/", methods=["GET"])
def admin_dashboard() -> str:
    """Render the admin dashboard."""
    return render_template(
        "admin/dashboard.html", admin_token=current_app.config["ADMIN_TOKEN"]
    )


@admin_bp.route("/variables", methods=["GET"])
@require_admin
def list_variables() -> tuple[dict[str, Any], int]:
    """List all persistent variables.

    Returns:
        JSON response with list of variables.
    """
    try:
        current_app.logger.info("=== Starting list_variables request ===")
        current_app.logger.info("Fetching all persistent variables")
        variables = PersistentVariable.query.all()
        current_app.logger.info("Found {len(variables)} variables")

        for var in variables:
            current_app.logger.info(
                "Variable: id=%s, name=%s, value=***REDACTED***", var.id, var.name
            )

        response = [
            {
                "id": var.id,
                "name": var.name,
                "value": var.value,
                "description": var.description,
                "created_at": var.created_at.isoformat() if var.created_at else None,
                "updated_at": var.updated_at.isoformat() if var.updated_at else None,
            }
            for var in variables
        ]
        current_app.logger.info("Returning response: {json.dumps(response, indent=2)}")
        return jsonify(response), 200
    except Exception as e:
        current_app.logger.exception("Error listing variables")
        return jsonify({"error": "Failed to list variables", "details": str(e)}), 500


@admin_bp.route("/variables", methods=["POST"])
@require_admin
def create_variable() -> tuple[dict[str, Any], int]:
    """Create a new persistent variable.

    Returns:
        JSON response with the created variable or error message.
    """
    try:
        data = request.get_json()
        if not data or not data.get("name") or not data.get("value"):
            return jsonify({"error": "Name and value are required"}), 400

        variable = PersistentVariable(
            name=data["name"], value=data["value"], description=data.get("description")
        )
        db.session.add(variable)
        db.session.commit()

        return jsonify(
            {
                "id": variable.id,
                "name": variable.name,
                "value": variable.value,
                "description": variable.description,
                "created_at": variable.created_at,
                "updated_at": variable.updated_at,
            }
        ), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception("Failed to create variable")
        return jsonify({"error": f"Failed to create variable: {e}"}), 400
    except Exception:
        current_app.logger.exception("Unexpected error creating variable")
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route("/variables/<int:item_id>", methods=["GET"])
def get_variable(item_id: int) -> tuple[dict[str, Any], int]:
    """Get a specific variable by ID.

    Args:
        item_id: Variable ID to retrieve.

    Returns:
        JSON response with variable details or error message.
    """
    variable = _get_item_by_id(PersistentVariable, item_id)
    return jsonify(
        {
            "id": variable.id,
            "name": variable.name,
            "value": variable.value,
            "description": variable.description,
            "created_at": variable.created_at,
            "updated_at": variable.updated_at,
        }
    ), 200


@admin_bp.route("/directories", methods=["GET"])
@require_admin
def list_directories() -> tuple[dict[str, Any], int]:
    """List all allowed directories.

    Returns:
        JSON response with list of directories.
    """
    try:
        directories = AllowedDirectory.query.all()
        return jsonify(
            [
                {
                    "id": d.id,
                    "path": d.path,
                    "description": d.description,
                    "is_recursive": d.is_recursive,
                    "created_at": d.created_at,
                    "updated_at": d.updated_at,
                }
                for d in directories
            ]
        ), 200
    except Exception:
        current_app.logger.exception("Error listing directories")
        return jsonify({"error": "Failed to list directories"}), 500


def _validate_directory_path(path_str: str) -> tuple[str, str | None]:
    """Validate and normalize directory path.

    Returns:
        Tuple of (normalized_path, error_message)
    """
    if not path_str or not isinstance(path_str, str):
        return "", "Path must be a non-empty string"

    try:
        path = Path(path_str.strip())
        if not path.is_absolute():
            path = path.resolve()

        path_str = str(path)

        suspicious_patterns = [
            r"^[A-Za-z]:\\Windows\\System32\\",
            r"^[A-Za-z]:\\Windows\\system32\\",
            r"^/etc/",
            r"^/var/",
            r"^/dev/",
            r"^/proc/",
            r"^/sys/",
        ]

        if any(
            re.search(pattern, path_str, re.IGNORECASE)
            for pattern in suspicious_patterns
        ):
            return "", "Cannot use system directories"
    except (OSError, ValueError) as e:
        return "", f"Invalid path format: {e!s}"
    else:
        return path_str, None


@admin_bp.route("/directories", methods=["POST"])
def create_directory() -> tuple[dict[str, Any], int]:
    """Create a new allowed directory."""
    try:
        data = request.get_json()
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid request format"}), 400

        raw_path = data.get("path", "")
        normalized_path, error = _validate_directory_path(raw_path)
        if error:
            return jsonify({"error": error}), 400

        # Check for existing directory
        existing_directory = AllowedDirectory.query.filter_by(
            path=normalized_path
        ).first()
        if existing_directory:
            # Update existing directory
            existing_directory.description = data.get(
                "description", existing_directory.description
            )
            existing_directory.is_recursive = data.get(
                "is_recursive", existing_directory.is_recursive
            )
            status_code = 200
            directory = existing_directory
        else:
            # Create new directory
            directory = AllowedDirectory(
                path=normalized_path,
                description=data.get("description", ""),
                is_recursive=data.get("is_recursive", False),
            )
            db.session.add(directory)
            status_code = 201

        db.session.commit()
        return jsonify(
            {
                "id": directory.id,
                "path": directory.path,
                "description": directory.description,
                "is_recursive": directory.is_recursive,
            }
        ), status_code

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {e!s}"}), 500
    except (BadRequest, ValueError) as e:
        return jsonify({"error": f"Bad request: {e!s}"}), 400


@admin_bp.route("/directories/<int:id>", methods=["GET"])
def get_directory(id: int) -> tuple[dict[str, Any], int]:
    """Get a directory by ID.

    Args:
        id: Directory ID

    Returns:
        JSON response with directory details
    """
    try:
        directory = AllowedDirectory.query.get_or_404(id)
        return jsonify(
            {
                "id": directory.id,
                "path": directory.path,
                "description": directory.description,
                "is_recursive": directory.is_recursive,
                "created_at": directory.created_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
                if directory.created_at
                else None,
                "updated_at": directory.updated_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
                if directory.updated_at
                else None,
            }
        ), 200
    except (SQLAlchemyError, NotFound) as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/directories/<int:id>", methods=["PUT"])
def update_directory(id: int) -> tuple[dict[str, Any], int]:
    try:
        directory = AllowedDirectory.query.get_or_404(id)
        data = request.get_json()
        if "path" in data:
            try:
                raw_path = data["path"].strip()
                if not raw_path:
                    return jsonify({"error": "Path cannot be empty"}), 400

                path = Path(raw_path)
                if not path.is_absolute():
                    path = path.resolve()

                path_str = str(path)

                # Only check for obviously dangerous patterns
                suspicious_patterns = [
                    r"^[A-Za-z]:\\Windows\\System32\\",  # System32 directory
                    r"^[A-Za-z]:\\Windows\\system32\\",  # System32 directory (case insensitive)
                    r"^/etc/",  # Linux system config
                    r"^/var/",  # Linux variable data
                    r"^/dev/",  # Linux device files
                    r"^/proc/",  # Linux process info
                    r"^/sys/",  # Linux system files
                ]

                for pattern in suspicious_patterns:
                    if re.search(pattern, path_str, re.IGNORECASE):
                        return jsonify({"error": "Cannot use system directories"}), 400

                path = str(path)

            except (ValueError, TypeError):
                return jsonify({"error": "Invalid path"}), 400

            directory.path = path
        if "description" in data:
            directory.description = data["description"]
        if "is_recursive" in data:
            directory.is_recursive = data["is_recursive"]

        db.session.commit()

        return jsonify(
            {
                "id": directory.id,
                "path": directory.path,
                "description": directory.description,
                "is_recursive": directory.is_recursive,
            }
        ), 200
    except (SQLAlchemyError, NotFound) as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/directories/<int:id>", methods=["DELETE"])
def delete_directory(id: int) -> tuple[str, int]:
    try:
        directory = AllowedDirectory.query.get(id)
        if not directory:
            current_app.logger.warning(
                "Attempted to delete non-existent directory with ID %s", id
            )
            return jsonify({"error": "Directory not found"}), 404

        try:
            db.session.delete(directory)
            db.session.commit()
            current_app.logger.info("Successfully deleted directory with ID %s", id)
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Database error deleting directory")
            return jsonify({"error": "Failed to delete directory"}), 500
        else:
            return "", 204
    except Exception:
        current_app.logger.exception(
            "Unexpected error in delete_directory",
        )
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route("/endpoints", methods=["GET"])
@require_admin
def list_endpoints() -> tuple[dict[str, Any], int]:
    """List all API endpoints."""
    try:
        endpoints = APIEndpoint.query.all()
        return jsonify(
            [
                {
                    "id": e.id,
                    "name": e.name,
                    "type": e.type,
                    "base_url": e.base_url,
                    "auth_type": e.auth_type,
                    "rate_limit": e.rate_limit,
                    "description": e.description,
                    "created_at": e.created_at,
                    "updated_at": e.updated_at,
                }
                for e in endpoints
            ]
        ), 200
    except Exception:
        current_app.logger.exception("Error listing endpoints:")
        return jsonify({"error": "Failed to list endpoints"}), 500


@admin_bp.route("/endpoints", methods=["POST"])
def create_endpoint() -> tuple[dict[str, Any], int]:
    """Create a new API endpoint."""
    data = request.get_json()
    if (
        not data
        or not data.get("name")
        or not data.get("base_url")
        or not data.get("type")
    ):
        msg = "Name, base_url, and type are required"
        raise BadRequest(msg)

    try:
        headers = data.get("headers", {})
        if isinstance(headers, str):
            try:
                headers = json.loads(headers)
            except json.JSONDecodeError:
                msg = "Invalid JSON format for headers"
                raise BadRequest(msg) from None

        endpoint = APIEndpoint(
            name=data["name"],
            base_url=data["base_url"],
            type=data["type"],
            auth_type=data.get("auth_type"),
            auth_token=data.get("auth_token"),
            headers=headers,
            rate_limit=data.get("rate_limit"),
            description=data.get("description"),
        )
        db.session.add(endpoint)
        db.session.commit()
        return jsonify(
            {
                "id": endpoint.id,
                "name": endpoint.name,
                "base_url": endpoint.base_url,
                "type": endpoint.type,
                "auth_type": endpoint.auth_type,
                "rate_limit": endpoint.rate_limit,
                "headers": endpoint.headers,
            }
        ), 201
    except (SQLAlchemyError, ValueError) as e:
        db.session.rollback()
        msg = f"Failed to create endpoint: {e!s}"
        raise BadRequest(msg) from e
    except BadRequest as e:
        db.session.rollback()
        msg = f"Error creating endpoint: {e!s}"
        raise BadRequest(msg) from e


@admin_bp.route("/endpoints/<int:item_id>", methods=["GET"])
def get_endpoint(item_id: int) -> tuple[dict[str, Any], int]:
    """Get a specific endpoint by ID."""
    endpoint = _get_item_by_id(APIEndpoint, item_id)
    return jsonify(
        {
            "id": endpoint.id,
            "name": endpoint.name,
            "base_url": endpoint.base_url,
            "type": endpoint.type,
            "auth_type": endpoint.auth_type,
            "auth_token": endpoint.auth_token,
            "headers": endpoint.headers,
            "rate_limit": endpoint.rate_limit,
            "description": endpoint.description,
            "created_at": endpoint.created_at,
            "updated_at": endpoint.updated_at,
        }
    ), 200


def _get_item_by_id(model, item_id: int) -> object | None:
    """Helper function to get an item by ID."""
    item = model.query.get(item_id)
    if not item:
        msg = f"{model.__name__} not found"
        raise NotFound(msg)
    return item


@admin_bp.route("/<string:model_type>/<int:item_id>", methods=["DELETE"])
def delete_item(model_type: str, item_id: int) -> tuple[str, int]:
    """Delete an item."""
    try:
        model_map = {
            "variables": PersistentVariable,
            "directories": AllowedDirectory,
            "endpoints": APIEndpoint,
        }

        model = model_map.get(model_type)
        if not model:
            current_app.logger.error("Invalid model type: {model_type}")
            return jsonify({"error": f"Invalid model type: {model_type}"}), 400

        item = model.query.get(item_id)
        if not item:
            msg = f"{model.__name__} with ID {item_id} not found"
            current_app.logger.error(msg)
            return jsonify({"error": msg}), 404

        try:
            db.session.delete(item)
            db.session.commit()
            current_app.logger.info("Successfully deleted")
            return jsonify({"message": f"{model.__name__} deleted successfully"}), 200
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Database error deleting")
            return jsonify({"error": f"Failed to delete {model.__name__}"}), 500
    except Exception:
        current_app.logger.exception("Unexpected error in delete_item:")
        return jsonify({"error": "Internal server error"}), 500


def _update_allowed_directory(
    directory: AllowedDirectory, data: dict
) -> dict[str, Any]:
    """Update an AllowedDirectory with the given data.

    Returns:
        Response data dictionary
    """

    def _validate_path(raw_path: str) -> str:
        """Validate and normalize directory path.

        Args:
            raw_path: Raw path string to validate

        Returns:
            Normalized path string

        Raises:
            ValueError: If path is invalid or points to system directory
        """
        if not raw_path.strip():
            msg = "Path cannot be empty"
            raise ValueError(msg)

        path = Path(raw_path)
        if not path.is_absolute():
            path = path.resolve()

        path_str = str(path)
        suspicious_patterns = [
            r"^[A-Za-z]:\\Windows\\System32\\",
            r"^[A-Za-z]:\\Windows\\system32\\",
            r"^/etc/",
            r"^/var/",
            r"^/dev/",
            r"^/proc/",
            r"^/sys/",
        ]

        if any(
            re.search(pattern, path_str, re.IGNORECASE)
            for pattern in suspicious_patterns
        ):
            msg = "Cannot use system directories"
            raise ValueError(msg)

        return str(path)

    if "path" in data:
        try:
            directory.path = _validate_path(data["path"])
        except (ValueError, TypeError, OSError) as e:
            msg = f"Invalid path: {e!s}"
            raise ValueError(msg) from e

    if "description" in data:
        directory.description = data["description"]
    if "is_recursive" in data:
        directory.is_recursive = data["is_recursive"]

    return {
        "id": directory.id,
        "path": directory.path,
        "description": directory.description,
        "is_recursive": directory.is_recursive,
    }


def _update_variable(variable: PersistentVariable, data: dict) -> dict[str, Any]:
    """Update a PersistentVariable with the given data.

    Returns:
        Response data dictionary
    """
    if "name" in data:
        variable.name = data["name"]
    if "description" in data:
        variable.description = data["description"]
    if "value" in data:
        variable.value = data["value"]

    return {
        "id": variable.id,
        "name": variable.name,
        "description": variable.description,
        "value": variable.value,
    }


@admin_bp.route("/<string:item_type>/<int:item_id>", methods=["PUT"])
def update_item(item_type: str, item_id: int) -> tuple[dict[str, Any], int]:
    """Update a specific item by type and ID."""
    try:
        item_class = _get_item_class(item_type)
        item = _get_item_by_id(item_class, item_id)
        data = request.get_json()

        if item_class == AllowedDirectory:
            response_data = _update_allowed_directory(item, data)
        else:
            response_data = _update_variable(item, data)

        db.session.commit()
        return jsonify(response_data), 200

    except (ValueError, TypeError, OSError) as e:
        db.session.rollback()
        return jsonify({"error": f"Invalid path: {e!s}"}), 400


def _get_item_class(item_type: str) -> type:
    """Helper function to get the item class by type."""
    normalized_type = item_type.rstrip("s")

    item_class = None
    if normalized_type == "variable":
        item_class = PersistentVariable
    elif normalized_type == "directory":
        item_class = AllowedDirectory
    elif normalized_type == "endpoint":
        item_class = APIEndpoint
    elif normalized_type == "api-key":
        item_class = APIKey

    if not item_class:
        msg = f"Invalid item type: {item_type}"
        raise BadRequest(msg)

    return item_class


@admin_bp.route("/api-keys", methods=["GET"])
@require_admin
def list_api_keys() -> tuple[dict[str, Any], int]:
    """List all API keys."""
    try:
        api_keys = []
        for key in session:
            if key.endswith("_token"):
                provider = key.replace("_token", "")
                current_app.logger.info(
                    "Process API key",
                    extra={"provider": provider, "action": "list_keys"},
                )
                api_keys.append(
                    {
                        "id": "***REDACTED***",
                        "name": f"{provider.title()} API key",
                        "provider": provider,
                        "created_at": session.get(f"{provider}_created_at"),
                        "last_used_at": session.get(f"{provider}_last_used_at"),
                        "revoked_at": session.get(f"{provider}_revoked_at"),
                    }
                )
        return jsonify(api_keys), 200
    except Exception:
        current_app.logger.exception("Error listing API keys")
        return jsonify({"error": "Failed to list API keys"}), 500


@admin_bp.route("/api-keys", methods=["POST"])
@require_admin
def create_api_key() -> tuple[dict[str, Any], int]:
    """Create a new API key."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is empty"}), 400

        provider = data.get("provider")
        token = data.get("token")

        if not provider:
            return jsonify({"error": "Provider is required"}), 400
        if not token:
            return jsonify({"error": "Token is required"}), 400

        session[f"{provider}_token"] = token
        session.modified = True
        return jsonify(
            {"message": f"{provider.title()} API key created successfully"}
        ), 201
    except Exception:
        current_app.logger.exception("Error processing API key creation request")
        return jsonify({"error": "Failed to create API key"}), 500


@admin_bp.route("/api-keys/<int:key_id>", methods=["GET"])
@require_admin
def get_api_key(key_id: int) -> tuple[dict[str, Any], int]:
    """Get a specific API key."""
    try:
        key = _get_item_by_id(APIKey, key_id)
        return jsonify(
            {
                "id": key.id,
                "name": key.name,
                "created_at": key.created_at,
                "last_used_at": key.last_used_at,
                "revoked_at": key.revoked_at,
            }
        ), 200
    except NotFound:
        return jsonify({"error": "API key not found"}), 404
    except Exception:
        current_app.logger.exception("Error retrieving API key")
        return jsonify({"error": "Failed to retrieve API key"}), 500


def _validate_api_key_update(data: dict, key_id: int) -> tuple[dict | None, str | None]:
    """Validate API key update data.

    Returns:
        Tuple of (validated_data, error_message)
    """
    validated_data = {}

    if "name" in data:
        existing_key = APIKey.query.filter(APIKey.name == data["name"]).first()
        if existing_key and existing_key.id != key_id:
            return None, "API key name already exists"
        validated_data["name"] = data["name"]

    if "key" in data:
        key = data["key"].strip()
        if not key:
            return None, "API key cannot be empty"
        if len(key) < MIN_API_KEY_LENGTH:
            msg = f"API key must be at least {MIN_API_KEY_LENGTH} characters long"
            raise ValueError(msg)
        validated_data["key"] = key

    return validated_data, None


@admin_bp.route("/api-key/<int:key_id>", methods=["PUT"])
@admin_bp.route("/api-keys/<int:key_id>", methods=["PUT"])
def update_api_key(key_id: int) -> tuple[dict[str, Any], int]:
    """Update an API key."""
    try:
        api_key = APIKey.query.get_or_404(key_id)
        data = request.get_json()

        # Validate update data
        validated_data, error = _validate_api_key_update(data, key_id)
        if error:
            return jsonify({"error": error}), 400

        # Update API key
        if "name" in validated_data:
            api_key.name = validated_data["name"]
        if "key" in validated_data:
            api_key.set_key(validated_data["key"])

        db.session.commit()

        return jsonify(
            {
                "id": api_key.id,
                "name": api_key.name,
                "created_at": api_key.created_at,
                "updated_at": api_key.updated_at,
            }
        ), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {e!s}"}), 500
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/api-key/<int:key_id>", methods=["DELETE"])
@admin_bp.route("/api-keys/<int:key_id>", methods=["DELETE"])
def delete_api_key(key_id: int) -> tuple[str, int]:
    """Delete an API key."""
    try:
        api_key = APIKey.query.get_or_404(key_id)
        db.session.delete(api_key)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {e!s}"}), 500
    else:
        return "", 204


@admin_bp.route("/token", methods=["GET"])
def get_admin_token() -> tuple[dict[str, Any], int]:
    """Get the admin token for client-side use"""

    if "admin_token" not in session:
        session["admin_token"] = current_app.config["ADMIN_TOKEN"]

    response = jsonify({"token": session["admin_token"]})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,X-Admin-Token")
    return response, 200


def _validate_github_token_request(data: Any) -> tuple[str | None, str | None]:
    """Validate GitHub token request data.

    Returns:
        Tuple of (token, error_message)
    """
    if not request.is_json:
        return None, "Request must be JSON"

    if not isinstance(data, dict):
        return None, "Invalid JSON format"

    token = data.get("token")
    if not token:
        return None, "Token is required"

    if not isinstance(token, str):
        return None, "Token must be a string"

    return token, None


def _setup_github_endpoint() -> tuple[APIEndpoint | None, str | None]:
    """Set up GitHub API endpoint.

    Returns:
        Tuple of (endpoint, error_message)
    """
    endpoint = APIEndpoint.query.filter_by(name="github").first()
    if not endpoint:
        endpoint = APIEndpoint(
            name="github",
            type="github",
            base_url="https://api.github.com",
            auth_type="bearer",
            headers={
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            description="GitHub API endpoint",
        )
        try:
            db.session.add(endpoint)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error creating GitHub endpoint: {e!s}"

    return endpoint, None


@admin_bp.route("/github/tokens", methods=["GET"])
@require_admin
def list_github_tokens() -> tuple[dict[str, Any], int]:
    """List all GitHub tokens."""
    try:
        token = session.get("github_token")
        if token:
            return jsonify(
                [
                    {
                        "id": "session",
                        "name": "GitHub Session Token",
                        "description": "Token stored in current session",
                        "created_at": None,
                        "updated_at": None,
                        "last_used": None,
                        "last_validated": None,
                        "is_active": True,
                        "is_valid": True,
                    }
                ]
            ), 200
        return jsonify([]), 200
    except Exception as e:
        current_app.logger.exception("Error listing GitHub tokens")
        return jsonify(
            {"error": "Failed to list GitHub tokens", "details": str(e)}
        ), 500


@admin_bp.route("/github/token", methods=["POST"])
@require_admin
def save_simple_github_token() -> tuple[dict[str, Any], int]:
    """Save the GitHub token in session."""
    try:
        # Validate request data
        token, error = _validate_github_token_request(request.get_json())
        if error:
            return jsonify({"error": error}), 400

        # Set up GitHub endpoint
        endpoint, error = _setup_github_endpoint()
        if error:
            return jsonify({"error": error}), 500

        # Validate token
        handler = GitHubAPIHandler(endpoint)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            is_valid, error_msg = loop.run_until_complete(handler.validate_token(token))
        except (ClientError, RequestException) as e:
            return jsonify({"error": f"Error validating token: {e!s}"}), 500
        finally:
            loop.close()

        if not is_valid:
            return jsonify({"error": f"Invalid token: {error_msg}"}), 400

        session["github_token"] = token
        session.modified = True

        return jsonify({"message": "GitHub token saved successfully"}), 200

    except Exception as e:
        current_app.logger.exception("Error saving GitHub token")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/github/token", methods=["GET"])
@require_admin
def get_simple_github_token() -> tuple[dict[str, Any], int]:
    """Get the stored GitHub token."""
    token = session.get("github_token")
    if token:
        return jsonify({"token": token}), 200
    return jsonify({"error": "No token found"}), 404
