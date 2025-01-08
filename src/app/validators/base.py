"""Base validator classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ValidationError(Exception):
    """Exception raised for validation errors."""


class BaseValidator(ABC):
    """Abstract base class for all validators."""

    @abstractmethod
    def validate(self, value: Any) -> None:
        """Validate a value.

        Args:
            value: The value to validate

        Raises:
            ValidationError: If validation fails
        """


class NonNullValidator(BaseValidator):
    """Validator that ensures a value is not null."""

    def validate(self, value: Any) -> None:
        """Validate that a value is not null or empty.

        Args:
            value: The value to validate

        Raises:
            ValidationError: If value is null or empty
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError("Value cannot be null or empty")
