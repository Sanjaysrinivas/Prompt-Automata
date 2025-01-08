"""File reference handler implementation."""

from __future__ import annotations

import logging
import os
from datetime import datetime

from src.app.models.reference_models import ReferenceType
from src.app.services.file_path_validator import FilePathValidator
from src.app.services.reference_handlers import (
    ReferenceHandler,
    ReferenceResolutionResult,
)

logger = logging.getLogger(__name__)


class FileReferenceHandler(ReferenceHandler):
    """Handler for file references with path restrictions."""

    @property
    def reference_type(self) -> ReferenceType:
        return ReferenceType.FILE

    async def validate(self, reference_value: str) -> tuple[bool, str | None]:
        """
        Validate file reference format and path restrictions.

        Args:
            reference_value: The file path to validate

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            if not reference_value:
                return False, "Empty file path"

            if not os.path.exists(reference_value):
                return False, f"File not found: {reference_value}"

            is_allowed, error, _ = await FilePathValidator.validate_path(
                reference_value
            )
            if not is_allowed:
                return False, error or "Path not allowed"

            return True, None

        except Exception as e:
            return False, f"Validation error: {e!s}"

    async def resolve(self, reference_value: str) -> ReferenceResolutionResult:
        """
        Resolve file reference by reading file contents.

        Args:
            reference_value: The file path to resolve

        Returns:
            ReferenceResolutionResult: Resolution result with content and metadata
        """
        try:
            is_valid, error = await self.validate(reference_value)
            if not is_valid:
                return ReferenceResolutionResult(success=False, error=error)

            metadata = {
                "path": reference_value,
                "size": os.path.getsize(reference_value),
                "modified": datetime.fromtimestamp(os.path.getmtime(reference_value)),
            }
            content = self.read_file(reference_value)

            return ReferenceResolutionResult(
                success=True,
                content=content,
                metadata=metadata,
            )

        except Exception as e:
            return ReferenceResolutionResult(
                success=False, error=f"Resolution error: {e!s}"
            )

    def read_file(self, file_path: str) -> str:
        """
        Read the contents of a file.

        Args:
            file_path: Path to the file to read

        Returns:
            str: Contents of the file

        Raises:
            FileNotFoundError: If the file does not exist
            IOError: If there is an error reading the file
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, encoding="latin-1") as f:
                return f.read()
