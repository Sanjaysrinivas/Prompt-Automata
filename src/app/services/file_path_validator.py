"""File path validation service."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from src.app import db
from src.app.models.reference_models import AllowedDirectory

# Configuration constants
EXCLUDED_DIRS = {".venv", ".env", "node_modules", "__pycache__", ".git"}
MAX_SUBDIR_FILES = 1000
ALLOWED_PATTERNS = ["*.py", "*.json", "*.yaml", "*.yml", "*.md"]


class FilePathValidator:
    """Validate file paths against allowed directories and rules."""

    @classmethod
    def normalize_path(cls, file_path: str) -> Path:
        """Normalize a file path."""
        try:
            return Path(file_path).resolve()
        except Exception as e:
            print(f"Error normalizing path {file_path}: {e}")
            raise

    @classmethod
    def is_allowed_file_type(cls, path: Path) -> bool:
        """Check if file type is allowed."""
        return any(
            fnmatch.fnmatch(path.name.lower(), pattern.lower())
            for pattern in ALLOWED_PATTERNS
        )

    @classmethod
    def is_excluded_dir(cls, path: Path) -> bool:
        """Check if path contains excluded directory."""
        parts = path.parts
        return any(excluded in parts for excluded in EXCLUDED_DIRS)

    @classmethod
    def has_too_many_files(cls, directory: Path) -> bool:
        """Check if directory has too many files."""
        try:
            count = sum(1 for _ in directory.glob("*"))
            return count > MAX_SUBDIR_FILES
        except Exception as e:
            print(f"Error counting files in {directory}: {e}")
            return False

    @classmethod
    def is_subpath(cls, path: Path, base_path: Path) -> bool:
        """Check if path is a subpath of base_path."""
        try:
            path.relative_to(base_path)
            return True
        except ValueError:
            return False

    @classmethod
    async def validate_path(cls, file_path: str) -> tuple[bool, str | None, str | None]:
        """
        Validate a file path against allowed directories and rules.

        Args:
            file_path: Path to validate

        Returns:
            (is_valid, error_message, file_validation_message)
        """
        try:
            print(f"[DEBUG] Starting validation for path: {file_path}")

            # Normalize the input path
            path = cls.normalize_path(file_path)
            print(f"[DEBUG] Normalized path: {path}")

            # Basic validation
            if not path.exists():
                print(f"[DEBUG] Path does not exist: {path}")
                return False, f"File not found: {file_path}", None

            if not path.is_file():
                print(f"[DEBUG] Not a file: {path}")
                return False, f"Not a file: {file_path}", None

            # Check file type first
            if not cls.is_allowed_file_type(path):
                print(f"[DEBUG] File type not allowed: {path.suffix}")
                return (
                    False,
                    f"File type not allowed. Must be one of: {', '.join(ALLOWED_PATTERNS)}",
                    None,
                )

            # Check for excluded directories in path
            if cls.is_excluded_dir(path):
                print("[DEBUG] Path contains excluded directory")
                return (
                    False,
                    f"Path contains excluded directory: {', '.join(EXCLUDED_DIRS)}",
                    None,
                )

            # Check parent directory file count
            if cls.has_too_many_files(path.parent):
                print("[DEBUG] Directory has too many files")
                return False, f"Directory has more than {MAX_SUBDIR_FILES} files", None

            # Get allowed directories
            allowed_dirs = db.session.query(AllowedDirectory).all()
            print(f"[DEBUG] Found {len(allowed_dirs)} allowed directories")

            if not allowed_dirs:
                print("[DEBUG] No allowed directories configured")
                return False, "No allowed directories configured", None

            # Check if path is within any allowed directory
            for allowed_dir in allowed_dirs:
                base_path = cls.normalize_path(allowed_dir.path)
                print(f"[DEBUG] Checking against allowed dir: {base_path}")

                if cls.is_subpath(path, base_path):
                    # If not recursive, the file must be directly in the allowed directory
                    if not allowed_dir.is_recursive and path.parent != base_path:
                        print(
                            f"[DEBUG] Directory {base_path} is not recursive and file is in subdirectory"
                        )
                        return True, None, "Allowed directory is not recursive"

                    print(f"[DEBUG] Path is valid within: {base_path}")
                    return True, None, "Inserted file in allowed directory"

            print("[DEBUG] Path is not within any allowed directory")
            return (
                False,
                "Path is not within any allowed directory",
                "Inserted file not in allowed directory",
            )

        except Exception as e:
            print(f"[DEBUG] Validation error: {e!s}")
            return False, f"Validation error: {e!s}", None
