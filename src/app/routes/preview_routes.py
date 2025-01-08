from __future__ import annotations

import json
import traceback

import requests
from flask import Blueprint, Response, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from src.app.models.api_endpoint import APIEndpoint
from src.app.models.reference_models import PersistentVariable
from src.app.services.file_path_validator import FilePathValidator
from src.app.services.file_reference_handler import FileReferenceHandler

preview_bp = Blueprint("preview", __name__)


@preview_bp.route("/api/preview/file", methods=["GET"])
async def preview_file():
    try:
        file_path = request.args.get("path")
        if not file_path:
            current_app.logger.warning("[API Preview] No file path provided")
            return jsonify({"error": "No file path provided"}), 400

        if file_path.startswith("@[file:") and file_path.endswith("]"):
            file_path = file_path[6:-1]

        validator = FilePathValidator()
        is_valid, error_message = await validator.validate_path(file_path)
        if not is_valid:
            current_app.logger.error("[API Preview] File path not allowed")
            return jsonify({"error": error_message}), 403

        handler = FileReferenceHandler()
        try:
            content = handler.read_file(file_path)
        except Exception as e:
            current_app.logger.exception("[API Preview] Error reading file")
            return jsonify({"error": f"Error reading file: {e!s}"}), 500

        try:
            token_service = current_app.token_service
            token_count, _ = await token_service.count_tokens(content)
            current_app.logger.info("Token count for file {file_path}: {token_count}")
        except Exception:
            current_app.logger.exception("Error counting tokens")
            token_count = None

        return jsonify(
            {"content": content, "path": file_path, "token_count": token_count}
        ), 200

    except Exception as e:
        current_app.logger.exception("[API Preview] Unexpected error")
        return jsonify({"error": f"Failed to get file content: {e!s}"}), 500


def _make_error_response(
    error: str, status_code: int = 400, details: str | None = None
) -> tuple[Response, int]:
    """Create a consistent error response."""
    response = {"error": error}
    if details:
        response["details"] = details
    return jsonify(response), status_code


def _get_endpoint(
    endpoint_name: str,
) -> tuple[APIEndpoint | None, tuple[Response, int] | None]:
    """Get endpoint from database with error handling."""
    if not endpoint_name:
        current_app.logger.warning("[API Preview] No endpoint name provided")
        return None, _make_error_response("No endpoint provided", 400)

    try:
        endpoint = APIEndpoint.query.filter_by(name=endpoint_name).first()
        if not endpoint:
            current_app.logger.error("[API Preview] Endpoint not found")
            return None, _make_error_response("Endpoint not found", 404)
        current_app.logger.info("[API Preview] Found endpoint")
    except SQLAlchemyError:
        current_app.logger.exception("[API Preview] Database error")
        return None, _make_error_response("Database error occurred", 500)
    return endpoint, None


def _prepare_request_params(
    endpoint: APIEndpoint, test_params: str
) -> tuple[dict, dict | None]:
    """Prepare headers and parameters for the request."""
    # Parse headers
    if isinstance(endpoint.headers, str):
        try:
            headers = json.loads(endpoint.headers)
        except json.JSONDecodeError:
            headers = {}
    elif isinstance(endpoint.headers, dict):
        headers = endpoint.headers
    else:
        headers = {}

    # Parse parameters
    try:
        params = json.loads(test_params)
    except json.JSONDecodeError:
        current_app.logger.exception("[API Preview] Invalid JSON in parameters")
        return headers, None

    # Add authentication
    if endpoint.auth_type == "token":
        headers["Authorization"] = f"Bearer {endpoint.auth_token}"
    elif endpoint.auth_type == "basic":
        import base64

        auth_string = base64.b64encode(f":{endpoint.auth_token}".encode()).decode()
        headers["Authorization"] = f"Basic {auth_string}"

    current_app.logger.info("[API Preview] Request setup completed")
    return headers, params


def _make_request(
    method: str, url: str, headers: dict, params: dict
) -> tuple[dict | None, tuple[Response, int] | None]:
    """Make HTTP request and process response."""
    try:
        current_app.logger.info("[API Preview] Making request")
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params if method == "GET" else None,
            json=params if method != "GET" else None,
            timeout=10,
        )

        try:
            response_data = response.json()
            content_type = "application/json"
        except json.JSONDecodeError:
            response_data = response.text
            content_type = response.headers.get("Content-Type", "text/plain")

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content_type": content_type,
            "content": response_data,
            "response_time": response.elapsed.total_seconds(),
        }, None

    except requests.exceptions.RequestException as e:
        current_app.logger.exception("[API Preview] Request failed")
        return None, _make_error_response("Request failed", 500, str(e))


@preview_bp.route("/api/preview/endpoint", methods=["GET"])
def preview_endpoint():
    """Preview an API endpoint by making a test request."""
    try:
        endpoint_name = request.args.get("endpoint")
        method = request.args.get("method", "GET").upper()
        test_params = request.args.get("params", "{}")

        current_app.logger.info("[API Preview] Received request")

        # Get endpoint
        endpoint, error_response = _get_endpoint(endpoint_name)
        if error_response:
            return error_response

        # Prepare request parameters
        headers, params = _prepare_request_params(endpoint, test_params)
        if params is None:
            return _make_error_response("Invalid JSON in parameters", 400)

        # Make request
        result, error_response = _make_request(
            method, endpoint.base_url, headers, params
        )
        if error_response:
            return error_response

        return jsonify(result)

    except Exception:
        current_app.logger.exception("[API Preview] Unexpected error")
        return _make_error_response("Unexpected error", 500)


@preview_bp.route("/api/preview/variable", methods=["GET"])
def preview_variable():
    try:
        var_name = request.args.get("name")
        if not var_name:
            current_app.logger.warning("[API Preview] No variable name provided")
            return jsonify({"error": "No variable name provided"}), 400

        try:
            variable = PersistentVariable.query.filter_by(name=var_name).first()
            if variable:
                current_app.logger.info("[API Preview] Found variable")
            else:
                current_app.logger.error("[API Preview] Variable not found")
                return jsonify({"error": "Variable not found"}), 404

        except SQLAlchemyError:
            current_app.logger.exception("[API Preview] Database error")
            return jsonify({"error": "Database error occurred"}), 500

        return jsonify(
            {
                "name": variable.name,
                "value": variable.value,
                "lastUpdated": variable.updated_at.isoformat(),
            }
        )

    except Exception as e:
        current_app.logger.exception("[API Preview] Unexpected error")
        current_app.logger.exception(traceback.format_exc())
        return jsonify({"error": f"Unexpected error: {e!s}"}), 500
