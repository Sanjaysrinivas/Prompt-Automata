"""API routes for managing reference system models."""

from __future__ import annotations

import os

from flask import Blueprint, request
from sqlalchemy.exc import SQLAlchemyError

from src.app import db
from src.app.models.api_endpoint import APIEndpoint
from src.app.models.api_models import APIResponseBuilder
from src.app.models.reference_models import (
    AllowedDirectory,
    PersistentVariable,
)
from src.app.utils.response_utils import (
    create_api_response,
    handle_db_error,
    serialize_directory,
    serialize_endpoint,
    serialize_variable,
)
from src.app.utils.validation_utils import RequestValidator, validate_json_request

references_bp = Blueprint("references", __name__, url_prefix="/api/references")


@references_bp.route("/variables", methods=["GET"])
def list_variables():
    """List all persistent variables."""
    variables = PersistentVariable.query.all()
    response = APIResponseBuilder.success(
        data=[serialize_variable(var) for var in variables]
    )
    return create_api_response(response)


@references_bp.route("/variables", methods=["POST"])
@validate_json_request
def create_variable():
    """Create a new persistent variable."""
    data = request.get_json()
    validation_error = RequestValidator.validate_variable_creation(data)
    if validation_error:
        return create_api_response(validation_error)

    try:
        variable = PersistentVariable(
            name=data["name"], value=data["value"], description=data.get("description")
        )
        db.session.add(variable)
        db.session.commit()

        response = APIResponseBuilder.success(
            data=serialize_variable(variable),
            status_code=201,
        )
        return create_api_response(response)
    except SQLAlchemyError as e:
        db.session.rollback()
        return handle_db_error(e, "variable creation")


@references_bp.route("/variables/<int:variable_id>", methods=["PUT"])
@validate_json_request
def update_variable(variable_id):
    """Update a persistent variable."""
    data = request.get_json()
    validation_error = RequestValidator.validate_update_request(data)
    if validation_error:
        return create_api_response(validation_error)

    try:
        variable = PersistentVariable.query.get_or_404(variable_id)
        if "name" in data:
            variable.name = data["name"]
        if "value" in data:
            variable.value = data["value"]
        if "description" in data:
            variable.description = data["description"]

        db.session.commit()
        response = APIResponseBuilder.success(data=serialize_variable(variable))
        return create_api_response(response)
    except SQLAlchemyError as e:
        db.session.rollback()
        return handle_db_error(e, "variable update")


@references_bp.route("/variables/<int:variable_id>", methods=["DELETE"])
def delete_variable(variable_id):
    """Delete a persistent variable."""
    try:
        variable = PersistentVariable.query.get_or_404(variable_id)
        db.session.delete(variable)
        db.session.commit()
        response = APIResponseBuilder.success(message="Variable deleted successfully")
        return create_api_response(response)
    except SQLAlchemyError as e:
        db.session.rollback()
        return handle_db_error(e, "variable deletion")


@references_bp.route("/directories", methods=["GET"])
def list_directories():
    """List all allowed directories."""
    directories = AllowedDirectory.query.all()
    response = APIResponseBuilder.success(
        data=[serialize_directory(dir) for dir in directories]
    )
    return create_api_response(response)


@references_bp.route("/directories", methods=["POST"])
@validate_json_request
def create_directory():
    """Create a new allowed directory."""
    data = request.get_json()
    validation_error = RequestValidator.validate_directory_creation(data)
    if validation_error:
        return create_api_response(validation_error)

    try:
        directory = AllowedDirectory(
            path=data["path"],
            description=data.get("description"),
            is_recursive=data.get("is_recursive", False),
        )
        db.session.add(directory)
        db.session.commit()

        response = APIResponseBuilder.success(
            data=serialize_directory(directory),
            status_code=201,
        )
        return create_api_response(response)
    except SQLAlchemyError as e:
        db.session.rollback()
        return handle_db_error(e, "directory creation")
    except Exception as e:
        db.session.rollback()
        return create_api_response(APIResponseBuilder.server_error(str(e)))


@references_bp.route("/directories/<int:directory_id>", methods=["PUT"])
@validate_json_request
def update_directory(directory_id):
    """Update an allowed directory."""
    data = request.get_json()
    validation_error = RequestValidator.validate_update_request(data)
    if validation_error:
        return create_api_response(validation_error)

    try:
        directory = AllowedDirectory.query.get_or_404(directory_id)
        if "path" in data:
            directory.path = data["path"]
        if "description" in data:
            directory.description = data["description"]
        if "is_recursive" in data:
            directory.is_recursive = data["is_recursive"]

        db.session.commit()
        response = APIResponseBuilder.success(data=serialize_directory(directory))
        return create_api_response(response)
    except SQLAlchemyError as e:
        db.session.rollback()
        return handle_db_error(e, "directory update")


@references_bp.route("/directories/<int:directory_id>", methods=["DELETE"])
def delete_directory(directory_id):
    """Delete an allowed directory."""
    try:
        directory = AllowedDirectory.query.get_or_404(directory_id)
        db.session.delete(directory)
        db.session.commit()
        response = APIResponseBuilder.success(message="Directory deleted successfully")
        return create_api_response(response)
    except SQLAlchemyError as e:
        db.session.rollback()
        return handle_db_error(e, "directory deletion")


@references_bp.route("/endpoints", methods=["GET"])
def list_endpoints():
    """List all API endpoints."""
    endpoints = APIEndpoint.query.all()
    response = APIResponseBuilder.success(
        data=[serialize_endpoint(endpoint) for endpoint in endpoints]
    )
    return create_api_response(response)


@references_bp.route("/endpoints", methods=["POST"])
@validate_json_request
def create_endpoint():
    """Create a new API endpoint."""
    data = request.get_json()
    validation_error = RequestValidator.validate_endpoint_creation(data)
    if validation_error:
        return create_api_response(validation_error)

    try:
        endpoint = APIEndpoint(
            name=data["name"],
            base_url=data["base_url"],
            type=data["type"],
            auth_type=data.get("auth_type"),
            auth_token=data.get("auth_token"),
            headers=data.get("headers"),
            rate_limit=data.get("rate_limit"),
            description=data.get("description"),
        )
        db.session.add(endpoint)
        db.session.commit()

        response = APIResponseBuilder.success(
            data=serialize_endpoint(endpoint),
            status_code=201,
        )
        return create_api_response(response)
    except SQLAlchemyError as e:
        db.session.rollback()
        return handle_db_error(e, "endpoint creation")


@references_bp.route("/endpoints/<int:endpoint_id>", methods=["PUT"])
@validate_json_request
def update_endpoint(endpoint_id):
    """Update an API endpoint."""
    data = request.get_json()
    validation_error = RequestValidator.validate_update_request(data)
    if validation_error:
        return create_api_response(validation_error)

    try:
        endpoint = APIEndpoint.query.get_or_404(endpoint_id)
        if "name" in data:
            endpoint.name = data["name"]
        if "base_url" in data:
            endpoint.base_url = data["base_url"]
        if "auth_type" in data:
            endpoint.auth_type = data["auth_type"]
        if "auth_token" in data:
            endpoint.auth_token = data["auth_token"]
        if "headers" in data:
            endpoint.headers = data["headers"]
        if "rate_limit" in data:
            endpoint.rate_limit = data["rate_limit"]
        if "description" in data:
            endpoint.description = data["description"]

        db.session.commit()
        response = APIResponseBuilder.success(data=serialize_endpoint(endpoint))
        return create_api_response(response)
    except SQLAlchemyError as e:
        db.session.rollback()
        return handle_db_error(e, "endpoint update")


@references_bp.route("/endpoints/<int:endpoint_id>", methods=["DELETE"])
def delete_endpoint(endpoint_id):
    """Delete an API endpoint."""
    try:
        endpoint = APIEndpoint.query.get_or_404(endpoint_id)
        db.session.delete(endpoint)
        db.session.commit()
        response = APIResponseBuilder.success(
            message="API endpoint deleted successfully"
        )
        return create_api_response(response)
    except SQLAlchemyError as e:
        db.session.rollback()
        return handle_db_error(e, "endpoint deletion")


@references_bp.route("/validate-path", methods=["POST"])
@validate_json_request
def validate_path():
    """Validate if a given path is within allowed directories."""
    data = request.get_json()
    validation_error = RequestValidator.validate_path_validation(data)
    if validation_error:
        return create_api_response(validation_error)

    path = os.path.abspath(data["path"])
    allowed_directories = AllowedDirectory.query.all()

    for directory in allowed_directories:
        allowed_path = os.path.abspath(directory.path)
        if path.startswith(allowed_path):
            if directory.is_recursive or os.path.dirname(path) == allowed_path:
                response = APIResponseBuilder.success(
                    data={"valid": True, "allowed_directory": directory.path}
                )
                return create_api_response(response)

    response = APIResponseBuilder.success(
        data={"valid": False, "message": "Path is not within any allowed directory"}
    )
    return create_api_response(response)
