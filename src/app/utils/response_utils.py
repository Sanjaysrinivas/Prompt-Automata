"""Utility functions for handling API responses."""

from __future__ import annotations

from typing import Any

from flask import jsonify
from sqlalchemy.exc import SQLAlchemyError

from src.app.models.api_endpoint import APIEndpoint
from src.app.models.api_models import APIResponse, APIResponseBuilder
from src.app.models.reference_models import (
    AllowedDirectory,
    PersistentVariable,
)


def create_api_response(response: APIResponse) -> tuple[Any, int]:
    """Create a Flask response from an APIResponse object.

    Args:
        response: APIResponse object containing response data

    Returns:
        A tuple of (response, status_code)
    """
    return jsonify(response.to_dict()), response.status_code


def handle_db_error(e: SQLAlchemyError, operation: str) -> tuple[Any, int]:
    """Handle database errors uniformly.

    Args:
        e: The SQLAlchemy error
        operation: Description of the operation that failed

    Returns:
        A tuple of (response, status_code)
    """
    response = APIResponseBuilder.error(
        error=f"Database error during {operation}: {e!s}",
        status_code=400,
    )
    return create_api_response(response)


def serialize_variable(variable: PersistentVariable) -> dict[str, Any]:
    """Serialize a PersistentVariable instance."""
    return {
        "id": variable.id,
        "name": variable.name,
        "value": variable.value,
        "description": variable.description,
        "created_at": variable.created_at,
        "updated_at": variable.updated_at,
    }


def serialize_directory(directory: AllowedDirectory) -> dict[str, Any]:
    """Serialize an AllowedDirectory instance."""
    return {
        "id": directory.id,
        "path": directory.path,
        "description": directory.description,
        "is_recursive": directory.is_recursive,
        "created_at": directory.created_at,
        "updated_at": directory.updated_at,
    }


def serialize_endpoint(endpoint: APIEndpoint) -> dict[str, Any]:
    """Serialize an APIEndpoint instance."""
    return {
        "id": endpoint.id,
        "name": endpoint.name,
        "type": endpoint.type,
        "base_url": endpoint.base_url,
        "auth_type": endpoint.auth_type,
        "headers": endpoint.headers,
        "rate_limit": endpoint.rate_limit,
        "description": endpoint.description,
        "created_at": endpoint.created_at,
        "updated_at": endpoint.updated_at,
    }
