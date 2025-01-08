"""Workspace utilities."""

from __future__ import annotations

import logging
from pathlib import Path

from flask import current_app

logger = logging.getLogger(__name__)


def get_workspace_path(*, strict: bool = False) -> Path:
    """Get the configured workspace path.

    Args:
        strict: If True, raise ValueError when WORKSPACE_PATH is not configured.
               If False, fall back to current working directory.

    Returns:
        Path: The configured workspace path or fallback path

    Raises:
        ValueError: If strict=True and WORKSPACE_PATH is not configured
    """
    workspace = current_app.config.get("WORKSPACE_PATH")

    if not workspace:
        if strict:
            msg = "WORKSPACE_PATH not configured"
            raise ValueError(msg)

        fallback = Path.cwd()
        logger.warning(
            "WORKSPACE_PATH not configured, falling back to current working directory: %s",
            fallback,
        )
        workspace = fallback

    return Path(workspace)
