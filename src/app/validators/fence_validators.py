"""Validators for fences, blocks, and references."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.app.models.reference_models import AllowedDirectory, PersistentVariable

from .base import BaseValidator, NonNullValidator, ValidationError


class FenceContentValidator(NonNullValidator):
    """Validator for fence content."""

    def validate(self, value: Any) -> None:
        """Validate fence content.

        Args:
            value: The fence content to validate

        Raises:
            ValidationError: If validation fails
        """
        if value is None or not str(value).strip():
            raise ValidationError("Fence content cannot be empty")


class BlockContentValidator(NonNullValidator):
    """Validator for block content."""

    def validate(self, value: Any) -> None:
        """Validate block content.

        Args:
            value: The block content to validate

        Raises:
            ValidationError: If validation fails
        """
        super().validate(value)

        # Only validate that the block has some whitespace or newline
        if not any(c.isspace() for c in str(value)):
            raise ValidationError("Block must contain at least whitespace or newline")


class FileReferenceValidator(BaseValidator):
    """Validator for file references."""

    def validate(self, path: str) -> None:
        """Validate a file reference path.

        Args:
            path: The path to validate

        Raises:
            ValidationError: If validation fails
        """
        if not path:
            raise ValidationError("File path cannot be empty")

        # Convert to Path object for validation
        path_obj = Path(path)

        # Check if path is absolute
        if not path_obj.is_absolute():
            raise ValidationError("File path must be absolute")

        # Check if path exists
        if not path_obj.exists():
            raise ValidationError(f"File path does not exist: {path}")

        # Check if path is within allowed directories
        allowed_dirs = [Path(d.path) for d in AllowedDirectory.query.all()]
        if not any(
            str(path_obj).startswith(str(allowed_dir)) for allowed_dir in allowed_dirs
        ):
            raise ValidationError(
                f"File path must be within allowed directories: {allowed_dirs}"
            )


class VariableReferenceValidator(BaseValidator):
    """Validator for variable references."""

    def validate(self, variable_name: str) -> None:
        """Validate a variable reference.

        Args:
            variable_name: The name of the variable to validate

        Raises:
            ValidationError: If validation fails
        """
        if not variable_name:
            raise ValidationError("Variable name cannot be empty")

        # Check if variable exists in persistent variables
        if not PersistentVariable.query.filter_by(name=variable_name).first():
            raise ValidationError(f"Variable does not exist: {variable_name}")
