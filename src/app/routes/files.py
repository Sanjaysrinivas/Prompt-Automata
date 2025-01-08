"""Routes for file operations."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select
from werkzeug.exceptions import BadRequest
from werkzeug.utils import secure_filename

if TYPE_CHECKING:
    from werkzeug.datastructures import FileStorage

from src.app.extensions import db
from src.app.models.reference_models import AllowedDirectory

files_bp = Blueprint("files", __name__, url_prefix="/api/files")


def get_workspace_path() -> Path:
    """Get the workspace path from the environment or use a default.

    Returns:
        Path: The workspace directory path.
    """
    return Path(current_app.config["WORKSPACE_PATH"])


def raise_bad_request(
    message: str, original_error: Exception | None = None
) -> NoReturn:
    """Raise a BadRequest with a message.

    Args:
        message: The error message
        original_error: The original exception that caused this error

    Raises:
        BadRequest: Always raises this exception
    """
    if original_error is not None:
        raise BadRequest(message) from original_error
    raise BadRequest(message)


def build_directory_tree(base_path: Path, current_path: Path) -> dict[str, Any]:
    """Build a directory tree structure.

    Args:
        base_path: The base workspace path
        current_path: The current directory path

    Returns:
        dict[str, Any]: Directory tree structure
    """
    tree = {
        "name": current_path.name or base_path.name,
        "path": str(current_path.relative_to(base_path))
        if current_path != base_path
        else "",
        "is_dir": True,
        "expanded": str(current_path.relative_to(base_path)) == "",
        "children": [],
    }

    try:
        for item in current_path.iterdir():
            if item.name.startswith("."):
                continue

            if item.is_dir():
                tree["children"].append(build_directory_tree(base_path, item))
    except PermissionError:
        logging.warning("Permission denied accessing directory")
    except OSError:
        logging.exception("Error accessing directory")

    return tree


def check_path_permissions(path: Path) -> tuple[bool, str | None]:
    """Check if we have sufficient permissions to access a path.

    Args:
        path: Path to check

    Returns:
        tuple[bool, str | None]: (has_permission, error_message)
    """
    try:
        if path.is_file():
            path.open("r").close()
        else:
            next(path.iterdir(), None)
    except PermissionError:
        return False, "Permission denied"
    except OSError:
        return False, "Access error"
    else:
        return True, None


@files_bp.route("/list")
def list_files() -> tuple[dict[str, Any], int]:
    """List files in the workspace.

    Returns:
        tuple[dict[str, Any], int]: JSON response with file list and HTTP status code.
    """
    try:
        workspace = get_workspace_path()
        current_path = request.args.get("path", "").strip()

        if not current_path:
            target_path = workspace

        elif Path(current_path).is_absolute():
            target_path = Path(current_path).resolve()
        else:
            target_path = (workspace / current_path).resolve()

        if not target_path.is_dir():
            raise_bad_request("Path is not a directory")

        if not target_path.exists():
            raise_bad_request("Path does not exist")

        files = []

        skip_patterns = {
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            "instance",
            "node_modules",
        }

        try:
            for path in target_path.iterdir():
                if path.name in skip_patterns or any(
                    part in skip_patterns for part in path.parts
                ):
                    continue

                try:
                    stat = path.stat()
                    files.append(
                        {
                            "name": path.name,
                            "path": str(path).replace("\\", "/"),
                            "is_dir": path.is_dir(),
                            "size": stat.st_size if path.is_file() else None,
                            "modified": datetime.fromtimestamp(
                                stat.st_mtime, tz=timezone.utc
                            ).isoformat(),
                        }
                    )
                except (PermissionError, OSError):
                    logging.warning("Error accessing")
                    continue

        except PermissionError as e:
            logging.exception("Permission denied accessing directory")
            raise_bad_request("Permission denied", e)
        except OSError as e:
            logging.exception("Error accessing directory")
            raise_bad_request("Failed to access directory", e)

        return jsonify(
            {
                "files": sorted(
                    files, key=lambda x: (not x["is_dir"], x["name"].lower())
                ),
                "current_path": str(target_path),
            }
        ), 200

    except BadRequest:
        raise
    except Exception as e:
        logging.exception("Unexpected error in list_files")
        raise_bad_request("Failed to list files", e)


@files_bp.route("/content")
def get_file_content() -> tuple[dict[str, str], int]:
    """Get the content of a file.

    Returns:
        tuple[dict[str, str], int]: JSON response with file content and HTTP status code.
    """
    try:
        file_path = request.args.get("path", "").strip()
        if not file_path:
            raise_bad_request("No file path provided")

        workspace = get_workspace_path()

        if Path(file_path).is_absolute():
            full_path = Path(file_path).resolve()
        else:
            full_path = (workspace / file_path).resolve()

        if not full_path.exists():
            raise_bad_request(f"File does not exist: {file_path}")

        if not full_path.is_file():
            raise_bad_request("Path is not a file")

        try:
            content = full_path.read_text(encoding="utf-8")
            rel_path = (
                str(full_path.relative_to(workspace)).replace("\\", "/")
                if str(full_path).startswith(str(workspace))
                else str(full_path)
            )
            return jsonify({"content": content, "path": rel_path}), 200
        except UnicodeDecodeError:
            return jsonify(
                {
                    "content": "[Binary file content not shown]",
                    "path": rel_path,
                    "is_binary": True,
                }
            ), 200
        except Exception:
            logging.exception("Error reading file")
            raise_bad_request("Failed to read file")

    except BadRequest:
        raise
    except Exception:
        logging.exception("Unexpected error in get_file_content")
        raise_bad_request("Failed to get file content")


@files_bp.route("/upload", methods=["POST"])
def upload_file() -> tuple[dict[str, str], int]:
    """Upload a file to the workspace.

    Returns:
        tuple[dict[str, str], int]: JSON response with file path and HTTP status code.
    """
    try:
        if "file" not in request.files:
            raise_bad_request("No file provided")

        file: FileStorage = request.files["file"]
        if not file.filename:
            raise_bad_request("No filename provided")

        uploads_dir = Path(current_app.config["UPLOAD_FOLDER"])

        allowed_dirs = AllowedDirectory.query.all()
        is_allowed = any(
            str(uploads_dir).startswith(str(Path(ad.path).resolve()))
            for ad in allowed_dirs
        )

        if not is_allowed:
            allowed_dir = AllowedDirectory(
                path=str(uploads_dir),
                description="Application uploads directory",
                is_recursive=True,
            )
            db.session.add(allowed_dir)
            db.session.commit()

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename_parts = secure_filename(file.filename).rsplit(".", 1)
        if len(filename_parts) > 1:
            safe_filename = f"{filename_parts[0]}_{timestamp}.{filename_parts[1]}"
        else:
            safe_filename = f"{filename_parts[0]}_{timestamp}"

        target_path = uploads_dir / safe_filename

        try:
            file.save(target_path)
            relative_path = f"uploads/{safe_filename}"
            return jsonify(
                {
                    "path": relative_path,
                    "name": file.filename,
                    "size": target_path.stat().st_size,
                }
            ), 201
        except OSError:
            logging.exception("Error saving uploaded file")
            raise_bad_request("Failed to save file")

    except BadRequest:
        raise
    except Exception as e:
        logging.exception("Unexpected error in upload_file")
        raise_bad_request("Failed to upload file", e)


def _validate_request_data() -> tuple[dict | None, tuple[dict[str, Any], int] | None]:
    """Validate request data.

    Returns:
        Tuple of (validated data, error response)
    """
    data = request.get_json()
    if not data or "path" not in data:
        return None, (jsonify({"error": "Path is required"}), 400)
    return data, None


def _validate_path_format(
    path: str,
) -> tuple[Path | None, tuple[dict[str, Any], int] | None]:
    """Validate and normalize file path.

    Returns:
        Tuple of (normalized path, error response)
    """
    try:
        if os.name == "nt":
            path = path.replace("/", "\\")
        full_path = Path(path).resolve()
    except (ValueError, OSError, RuntimeError) as e:
        return None, (jsonify({"error": f"Invalid path format: {e!s}"}), 400)
    return full_path, None


def _check_path_exists(path: Path) -> tuple[dict[str, Any], int] | None:
    """Check if path exists.

    Returns:
        Error response if path doesn't exist, None otherwise
    """
    if not path.exists():
        return jsonify({"error": "Path does not exist"}), 404
    return None


def _validate_allowed_directories(path: Path) -> tuple[dict[str, Any], int] | None:
    """Check if path is within allowed directories.

    Returns:
        Error response if validation fails, None otherwise
    """
    allowed_dirs = db.session.scalars(select(AllowedDirectory)).all()
    if not allowed_dirs:
        return jsonify({"error": "No allowed directories configured"}), 400

    for allowed_dir in allowed_dirs:
        allowed_path = Path(allowed_dir.path).resolve()
        try:
            if path.is_relative_to(allowed_path):
                if allowed_dir.is_recursive:
                    return None
                # Non-recursive: only allow direct children
                if path.parent == allowed_path:
                    return None
        except ValueError:
            continue

    return jsonify({"error": "Path is not within allowed directories"}), 403


@files_bp.route("/validate", methods=["POST"])
def validate_file_path() -> tuple[dict[str, Any], int]:
    """Validate if a file path is within allowed directories."""
    try:
        # Validate request data
        data, error = _validate_request_data()
        if error:
            return error

        # Validate path format
        full_path, error = _validate_path_format(data["path"])
        if error:
            return error

        # Check if path exists
        error = _check_path_exists(full_path)
        if error:
            return error

        # Validate against allowed directories
        error = _validate_allowed_directories(full_path)
        if error:
            return error

        return jsonify({"valid": True}), 200

    except Exception:
        current_app.logger.exception("Error validating file path")
        return jsonify({"error": "An unexpected error occurred"}), 500


@files_bp.route("/tree", methods=["GET"])
def get_file_tree() -> tuple[dict[str, Any], int]:
    """Get a file tree structure for a given path.

    Returns:
        tuple[dict[str, Any], int]: JSON response with file tree and HTTP status code.
    """
    try:
        path = request.args.get("path")
        if not path:
            return jsonify({"error": "No path provided"}), 400

        try:
            if os.name == "nt":
                path = path.replace("/", "\\")
            full_path = Path(path).resolve()
        except Exception:
            current_app.logger.exception("Error resolving path")
            return jsonify({"error": "Invalid path format"}), 400

        if not full_path.exists():
            return jsonify({"error": "Path does not exist"}), 404

        has_permission, error = check_path_permissions(full_path)
        if not has_permission:
            return jsonify({"error": error}), 403

        tree = build_file_tree(full_path)
        return jsonify({"tree": tree}), 200

    except Exception:
        current_app.logger.exception("Error getting file tree")
        return jsonify({"error": "An unexpected error occurred"}), 500


def build_file_tree(path: Path) -> dict[str, Any] | str:
    """Build a tree structure for a given path.

    Args:
        path: Path to build tree for

    Returns:
        dict[str, Any] | str: Tree structure or file name
    """
    try:
        has_permission, error = check_path_permissions(path)
        if not has_permission:
            return f"{path.name} <{error}>"

        if path.is_file():
            return path.name

        if path.is_dir():
            children = []
            try:
                for child in path.iterdir():
                    if child.name.startswith(".") or child.name in {
                        "__pycache__",
                        "node_modules",
                        ".git",
                    }:
                        continue
                    children.append(build_file_tree(child))

                children.sort(
                    key=lambda x: (
                        isinstance(x, str),
                        x if isinstance(x, str) else next(iter(x.keys())).lower(),
                    )
                )

            except PermissionError:
                return {path.name: ["<Permission Denied>"]}
            except OSError:
                return {path.name: ["<Access Error>"]}

            return {path.name: children}

    except Exception:
        current_app.logger.exception("Error building tree for path")
        return f"{path.name} <Error>"


@files_bp.route("/stats")
def get_file_stats():
    """Get stats for a file or directory."""
    try:
        path = request.args.get("path")
        if not path:
            return jsonify({"error": "No path provided"}), 400

        try:
            if os.name == "nt":
                path = path.replace("/", "\\")
            path = Path(path).resolve()
        except Exception:
            current_app.logger.exception("Error resolving path")
            return jsonify({"error": "Invalid path format"}), 400

        if not path.exists():
            return jsonify({"error": "Path does not exist"}), 404

        stats = {
            "exists": True,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "name": path.name,
            "parent": str(path.parent),
        }

        return jsonify(stats), 200

    except Exception:
        current_app.logger.exception("Error getting file stats")
        return jsonify({"error": "An unexpected error occurred"}), 500
