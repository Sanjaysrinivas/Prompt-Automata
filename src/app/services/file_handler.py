"""Service for handling file operations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from werkzeug.utils import secure_filename


class FileHandler:
    """Handler for file-related operations."""

    FILE_PATTERN = re.compile(r"@\[(.*?)\]")

    def __init__(self, base_path: str | Path) -> None:
        """Initialize the file handler.

        Args:
            base_path: Base path for file operations.
        """
        self.base_path = Path(base_path)

    def extract_file_references(self, content: str) -> list[str]:
        """Extract file references from content.

        Args:
            content: The content to parse for file references.

        Returns:
            list[str]: List of file references found in the content.
        """
        return [match.group(1) for match in self.FILE_PATTERN.finditer(content)]

    def read_file_content(self, file_path: str) -> str | None:
        """Read content from a file.

        Args:
            file_path: Path to the file to read.

        Returns:
            str | None: File content if successful, None otherwise.
        """
        try:
            full_path = (self.base_path / file_path).resolve()
            if not str(full_path).startswith(str(self.base_path)):
                return None  # Prevent directory traversal
            if not full_path.is_file():
                return None
            content = full_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        else:
            return content

    def resolve_file_references(self, content: str) -> dict[str, Any]:
        """Resolve file references in content.

        Args:
            content: Content containing file references.

        Returns:
            dict[str, Any]: Dictionary with resolved file contents and metadata.
        """
        files = {}
        for ref in self.extract_file_references(content):
            file_content = self.read_file_content(ref)
            if file_content is not None:
                files[ref] = {
                    "content": file_content,
                    "path": ref,
                    "filename": Path(ref).name,
                }
        return files

    def save_file(self, file_data: bytes, filename: str) -> str | None:
        """Save a file to the base path.

        Args:
            file_data: The file data to save.
            filename: Original filename.

        Returns:
            str | None: Saved file path if successful, None otherwise.
        """
        try:
            safe_filename = secure_filename(filename)
            file_path = self.base_path / safe_filename
            file_path.write_bytes(file_data)
        except (OSError, ValueError):
            return None
        else:
            return str(file_path.relative_to(self.base_path))
