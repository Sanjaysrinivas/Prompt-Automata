"""File content handler module."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiofiles

from src.app.utils.exceptions import ReferenceError

from .reference_handler import ReferenceHandler

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class FileHandler(ReferenceHandler):
    """Handler for file references with streaming support."""

    CHUNK_SIZE = 8192

    def __init__(self):
        """Initialize file handler."""
        super().__init__()

    async def get_content(self, filepath: str) -> AsyncGenerator[str, None]:
        """Get content from file in chunks.

        Args:
            filepath: Path to file or dict with 'path' key

        Yields:
            Chunks of file content

        Raises:
            ReferenceError: If file cannot be read
        """
        if isinstance(filepath, dict):
            filepath = filepath.get("path")

        if not filepath:
            msg = "Missing file path"
            raise ReferenceError(msg)

        path = Path(filepath)
        if not path.exists():
            msg = f"File not found: {filepath}"
            raise ReferenceError(msg)

        try:
            async with aiofiles("r", encoding="utf-8") as f:  # Async-friendly file open
                while chunk := await f.read(self.CHUNK_SIZE):  # Use async read
                    yield chunk
        except OSError as e:
            msg = f"Failed to read file {filepath}: {e!s}"
            raise ReferenceError(msg) from e

    def get_cache_key(self, reference: dict[str, Any]) -> str:
        """Get cache key based on file path and modification time.

        Args:
            reference: Reference configuration with file path

        Returns:
            Cache key string

        Raises:
            ReferenceError: If file info cannot be retrieved
        """
        file_path = reference.get("path")
        if not file_path:
            msg = "Invalid file path: Missing 'path' key"
            raise ReferenceError(msg)

        path = Path(file_path)
        if not path.is_file():
            msg = f"Invalid file path: {file_path}"
            raise ReferenceError(msg)

        try:
            mtime = path.stat().st_mtime

        except OSError as e:
            msg = f"Failed to get file info for {file_path}: {e!s}"
            raise ReferenceError(msg) from e

        else:
            return f"file:{file_path}:{mtime}"

    def should_recount(
        self, reference: dict[str, Any], cached_info: dict[str, Any] | None = None
    ) -> bool:
        """Check if file has been modified since last count.

        Args:
            reference: Reference configuration with file path
            cached_info: Previously cached counting info

        Returns:
            True if file has been modified

        Raises:
            ReferenceError: If file info cannot be retrieved
        """
        if not cached_info:
            return True

        file_path = reference.get("path")
        if not file_path:
            msg = "Invalid file path: Missing 'path' key"
            raise ReferenceError(msg)

        path = Path(file_path)
        if not path.is_file():
            msg = f"Invalid file path: {file_path}"
            raise ReferenceError(msg)

        try:
            current_mtime = path.stat().st_mtime  # Use Path.stat()
            cached_mtime = float(cached_info.get("mtime", 0))
        except OSError as e:
            msg = f"Failed to check file modification for {file_path}: {e!s}"
            raise ReferenceError(msg) from e
        else:
            return current_mtime > cached_mtime

    def get_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file contents.

        Args:
            file_path: Path to the file

        Returns:
            SHA-256 hash of file contents

        Raises:
            ReferenceError: If file cannot be read
        """
        path = Path(file_path)
        if not path.is_file():
            msg = f"Invalid file path: {file_path}"
            raise ReferenceError(msg)

        try:
            sha256 = hashlib.sha256()
            with path.open("rb") as f:  # Use Path.open()
                while chunk := f.read(self.CHUNK_SIZE):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except OSError as e:
            msg = f"Failed to calculate hash for {file_path}: {e!s}"
            raise ReferenceError(msg) from e
