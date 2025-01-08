"""Utility functions for request validation."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import request

from src.app.models.api_models import APIResponse
from src.app.utils.response_utils import create_api_response
from src.app.validators.base import ValidationError
from src.app.validators.fence_validators import (
    BlockContentValidator,
    FenceContentValidator,
    FileReferenceValidator,
    VariableReferenceValidator,
)

fence_validator = FenceContentValidator()
block_validator = BlockContentValidator()
file_validator = FileReferenceValidator()
variable_validator = VariableReferenceValidator()


def validate_json_request(func: Callable) -> Callable:
    """Decorator to validate that the request has JSON content type."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not request.is_json:
            return create_api_response(
                success=False, message="Content-Type must be application/json"
            )
        return func(*args, **kwargs)

    return wrapper


def validate_required_fields(
    data: dict[str, Any], required_fields: list[str]
) -> APIResponse | None:
    """Validate that all required fields are present in the data.

    Args:
        data: The data to validate
        required_fields: List of required field names

    Returns:
        APIResponse if validation fails, None if validation succeeds
    """
    if not data:
        return create_api_response(success=False, message="No data provided")

    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return create_api_response(
            success=False,
            message=f"Missing required fields: {', '.join(missing_fields)}",
        )

    return None


class RequestValidator:
    """Validator for various request types."""

    @staticmethod
    def validate_fence(data: dict[str, Any]) -> APIResponse | None:
        """Validate fence data."""
        validation_error = validate_required_fields(data, ["content"])
        if validation_error:
            return validation_error

        try:
            fence_validator.validate(data["content"])
            return None
        except ValidationError as e:
            return create_api_response(success=False, message=str(e))

    @staticmethod
    def validate_block(data: dict[str, Any]) -> APIResponse | None:
        """Validate block data."""
        validation_error = validate_required_fields(data, ["content"])
        if validation_error:
            return validation_error

        try:
            block_validator.validate(data["content"])
            return None
        except ValidationError as e:
            return create_api_response(success=False, message=str(e))

    @staticmethod
    def validate_file_reference(data: dict[str, Any]) -> APIResponse | None:
        """Validate file reference data."""
        validation_error = validate_required_fields(data, ["path"])
        if validation_error:
            return validation_error

        try:
            file_validator.validate(data["path"])
            return None
        except ValidationError as e:
            return create_api_response(success=False, message=str(e))

    @staticmethod
    def validate_variable_reference(data: dict[str, Any]) -> APIResponse | None:
        """Validate variable reference data."""
        validation_error = validate_required_fields(data, ["name"])
        if validation_error:
            return validation_error

        try:
            variable_validator.validate(data["name"])
            return None
        except ValidationError as e:
            return create_api_response(success=False, message=str(e))

    @staticmethod
    def validate_variable_creation(data: dict[str, Any]) -> APIResponse | None:
        """Validate variable creation request data."""
        return validate_required_fields(data, ["name", "value"])

    @staticmethod
    def validate_directory_creation(data: dict[str, Any]) -> APIResponse | None:
        """Validate directory creation request data."""
        return validate_required_fields(data, ["path"])

    @staticmethod
    def validate_endpoint_creation(data: dict[str, Any]) -> APIResponse | None:
        """Validate endpoint creation request data."""
        return validate_required_fields(data, ["url", "method"])

    @staticmethod
    def validate_path_validation(data: dict[str, Any]) -> APIResponse | None:
        """Validate path validation request data."""
        return validate_required_fields(data, ["path"])

    @staticmethod
    def validate_update_request(data: dict[str, Any]) -> APIResponse | None:
        """Validate update request data."""
        if not data:
            return create_api_response(success=False, message="No data provided")
        return None
