"""Routes for fence content refresh operations."""

from __future__ import annotations

import logging
import re

from flask import Blueprint, jsonify, request

from src.app.services.global_token_counter import GlobalTokenCounter
from src.app.services.reference_service import ReferenceService
from src.app.services.refresh_service import RefreshService
from src.app.utils.exceptions import RefreshError

logger = logging.getLogger(__name__)
refresh_bp = Blueprint("refresh", __name__)

reference_service = ReferenceService()
global_token_counter = GlobalTokenCounter()
refresh_service = RefreshService(reference_service, global_token_counter)


@refresh_bp.route("/api/refresh/block/<block_id>", methods=["POST"])
async def refresh_block(block_id: str):
    """Refresh a single fence block.

    Args:
        block_id: ID of the block to refresh
    """
    # Validate block_id format
    if not re.match(r"^[a-zA-Z0-9_-]+$", block_id):
        return jsonify(
            {
                "status": "error",
                "message": "Invalid block ID format. Only alphanumeric characters, underscores, and hyphens are allowed.",
            }
        ), 400

    try:
        data = request.get_json() or {}
        content = data.get("content")

        result = await refresh_service.refresh_block(block_id, content=content)

        # Get the global token count after updating the block
        total_tokens = global_token_counter.total_tokens

        return jsonify(
            {
                "status": "success",
                "total_tokens": total_tokens,  # Use the actual global total
                "block_tokens": {block_id: result["token_count"]},
                "content": None,
            }
        )
    except RefreshError as e:
        logger.error(f"Error refreshing block {block_id}: {e!s}")
        return jsonify(
            {
                "status": "error",
                "error": str(e),
                "total_tokens": 0,
                "block_tokens": {},
                "content": None,
            }
        ), 400


@refresh_bp.route("/api/refresh/all", methods=["POST"])
async def refresh_all():
    """Refresh all fence blocks."""
    try:
        data = request.get_json() or {}
        logger.debug(f"Received blocks for refresh: {data}")

        blocks = data.get("blocks", [])
        contents = data.get("contents", {})

        if not isinstance(blocks, list):
            logger.error(f"Invalid blocks format: {blocks}")
            return jsonify(
                {
                    "status": "error",
                    "error": "Invalid blocks format",
                    "total_tokens": 0,
                    "block_tokens": {},
                }
            ), 400

        result = await refresh_service.refresh_all(blocks, contents=contents)

        return jsonify(result)

    except RefreshError as e:
        logger.error(f"Error during global refresh: {e!s}")
        return jsonify(
            {"status": "error", "error": str(e), "total_tokens": 0, "block_tokens": {}}
        ), 400
