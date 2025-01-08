"""Validators for prompts."""

from __future__ import annotations

import re
from typing import Any

from .base import NonNullValidator, ValidationError


class PromptValidator(NonNullValidator):
    """Validator for prompt content."""

    def validate(self, value: Any) -> None:
        """Validate prompt content.

        Args:
            value: The prompt content to validate

        Raises:
            ValidationError: If validation fails
        """
        super().validate(value)

        # Check for at least one reference in any fence content
        content = str(value)
        reference_pattern = r"@\[(var|github|api|file):[^\]]+\]"
        if not re.search(reference_pattern, content):
            raise ValidationError(
                "Prompt must contain at least one reference in the format @[type:name] where type is var, github, api, or file"
            )


class PromptContentValidator(NonNullValidator):
    """Validator for prompt content."""

    def validate(self, value: Any) -> None:
        """Validate prompt content.

        Args:
            value: The prompt content to validate

        Raises:
            ValidationError: If validation fails
        """
        super().validate(value)

        content = str(value)
        reference_pattern = r"@\[(var|github|api|file):[^\]]+\]"
        if not re.search(reference_pattern, content):
            raise ValidationError(
                "Prompt must contain at least one reference in the format @[type:name] where type is var, github, api, or file"
            )


class PromptFenceValidator(NonNullValidator):
    """Validator for prompt fences."""

    def validate(self, fences: list[dict]) -> None:
        """Validate prompt fences.

        Args:
            fences: List of fence dictionaries to validate

        Raises:
            ValidationError: If validation fails
        """
        super().validate(fences)

        if not fences:
            raise ValidationError("Prompt must contain at least one fence")

        has_reference = False
        reference_pattern = r"@\[(var|github|api|file):[^\]]+\]"

        for fence in fences:
            content = fence.get("content", "")
            if re.search(reference_pattern, str(content)):
                has_reference = True
                break

        if not has_reference:
            raise ValidationError(
                "At least one fence must contain a reference in the format @[type:name] where type is var, github, api, or file"
            )
