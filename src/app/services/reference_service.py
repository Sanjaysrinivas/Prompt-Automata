"""Service for handling fence references."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING

from src.app import db
from src.app.models.api_endpoint import APIEndpoint
from src.app.models.reference_models import (
    AllowedDirectory,
    FenceReference,
    PersistentVariable,
    ReferenceType,
)
from src.app.services.api_handler_factory import APIHandlerFactory

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class ReferenceService:
    """Service for managing fence references."""

    REFERENCE_PATTERN = r"\{\{([^:]+):([^}]+)\}\}"

    @classmethod
    def extract_references(cls, content: str) -> list[tuple[str, str]]:
        """Extract references from fence content."""
        matches = re.finditer(cls.REFERENCE_PATTERN, content)
        return [(match.group(1), match.group(2)) for match in matches]

    @staticmethod
    async def validate_reference(
        reference_type: ReferenceType, value: str
    ) -> tuple[bool, str | None]:
        """Validate a reference based on its type."""
        is_valid = False
        error: str | None = None

        try:
            if reference_type == ReferenceType.FILE:
                is_valid = await AllowedDirectory.is_path_allowed(value)
                if not is_valid:
                    error = f"Path '{value}' is not allowed"
            elif reference_type == ReferenceType.VARIABLE:
                variable = PersistentVariable.query.filter_by(name=value).first()
                if variable is None:
                    error = f"Variable '{value}' not found"
                else:
                    is_valid = True
            elif reference_type == ReferenceType.API:
                endpoint = APIEndpoint.query.filter_by(name=value).first()
                if endpoint is None:
                    error = f"API endpoint '{value}' not found"
                else:
                    handler = APIHandlerFactory.create_handler(endpoint)
                    iv = await handler.validate_configuration()
                    if iv:
                        is_valid = True
                    else:
                        error = "Invalid API configuration"
            else:
                logger.warning(
                    f"Validation not implemented for reference type: {reference_type}"
                )
                error = f"Validation not implemented for type: {reference_type}"

        except (OSError, ValueError, RuntimeError) as e:
            error = str(e)

        return is_valid, error

    @classmethod
    async def create_fence_references(
        cls, fence_id: int, content: str
    ) -> tuple[list[FenceReference], str | None]:
        """Create FenceReference objects for a fence."""
        references: list[FenceReference] = []
        error: str | None = None

        try:
            for ref_type, ref_value in cls.extract_references(content):
                reference_type = ReferenceType(ref_type)

                reference = FenceReference(
                    fence_id=fence_id,
                    reference_type=reference_type,
                    reference_value=ref_value,
                )

                is_valid, ref_error = await cls.validate_reference(
                    reference_type, ref_value
                )
                if not is_valid:
                    reference.error_message = ref_error
                else:
                    references.append(reference)
                    db.session.add(reference)

        except (OSError, ValueError, RuntimeError) as e:
            error = str(e)

        return references, error

    @staticmethod
    async def _get_file_content(reference_value: str) -> tuple[str, str | None]:
        """Get content for FILE reference type."""
        is_allowed, err = await AllowedDirectory.is_path_allowed(reference_value)
        if not is_allowed:
            return "", err

        path = Path(reference_value)
        if not path.exists():
            return "", f"File not found: {reference_value}"

        try:
            content = await asyncio.to_thread(path.read_text, encoding="utf-8")
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error getting file content: {e}", exc_info=True)
            return "", f"Error getting file content: {e!s}"
        else:
            return content, None

    @staticmethod
    async def _get_variable_content(reference_value: str) -> tuple[str, str | None]:
        """Get content for VARIABLE reference type."""
        try:
            variable = PersistentVariable.query.filter_by(name=reference_value).first()
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error getting variable content: {e}", exc_info=True)
            return "", f"Error getting variable content: {e!s}"
        else:
            if variable is None:
                return "", f"Variable not found: {reference_value}"
            return str(variable.value), None

    @staticmethod
    async def _get_api_content(reference_value: str) -> tuple[str, str | None]:
        """Get content for API reference type."""
        try:
            endpoint = APIEndpoint.query.filter_by(name=reference_value).first()
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error getting API content: {e}", exc_info=True)
            return "", f"Error getting API content: {e!s}"
        else:
            if endpoint is None:
                return "", f"API endpoint not found: {reference_value}"

            handler = APIHandlerFactory.create_handler(endpoint)
            response = await handler.get_resource("")
            return str(response), None

    @staticmethod
    async def get_reference_content(
        reference: FenceReference,
    ) -> tuple[str, str | None]:
        """Get the content of a reference for token counting."""
        reference_type_to_method: dict[
            ReferenceType, Callable[[str], Awaitable[tuple[str, str | None]]]
        ] = {
            ReferenceType.FILE: ReferenceService._get_file_content,
            ReferenceType.VARIABLE: ReferenceService._get_variable_content,
            ReferenceType.API: ReferenceService._get_api_content,
        }

        method = reference_type_to_method.get(reference.reference_type)
        if method is None:
            logger.error(
                f"Unhandled reference type: {reference.reference_type}",
                extra={
                    "reference_id": reference.id,
                    "fence_id": reference.fence_id,
                    "reference_value": reference.reference_value,
                },
            )
            return "", f"Unknown reference type: {reference.reference_type}"

        try:
            return await method(reference.reference_value)
        except Exception as e:
            logger.error(
                f"Error processing reference content: {e}",
                exc_info=True,
                extra={
                    "reference_type": reference.reference_type,
                    "reference_id": reference.id,
                    "fence_id": reference.fence_id,
                },
            )
            return "", f"Error processing reference: {e!s}"

    @classmethod
    async def get_all_reference_content(
        cls, references: list[FenceReference]
    ) -> dict[str, str]:
        """Get content for multiple references."""
        contents: dict[str, str] = {}
        for ref in references:
            content, error = await cls.get_reference_content(ref)
            if error:
                logger.warning(
                    f"Reference error: {error}",
                    extra={
                        "reference_id": ref.id,
                        "fence_id": ref.fence_id,
                        "reference_type": ref.reference_type,
                    },
                )
                ref.error_message = error
            contents[str(ref.id)] = content
        return contents
