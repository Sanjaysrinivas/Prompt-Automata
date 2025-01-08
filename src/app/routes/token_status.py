"""Token status routes."""

from __future__ import annotations

import asyncio
import logging
import uuid
from functools import wraps

from flask import Blueprint, current_app, jsonify, request, session

from src.app.services.error_notification import ErrorNotificationService, ErrorSeverity
from src.app.services.global_token_counter import (
    GlobalTokenCounter,
)

logger = logging.getLogger(__name__)

token_status_bp = Blueprint("token_status", __name__)
token_counter = GlobalTokenCounter()
error_service = ErrorNotificationService()


def async_route(f):
    """Decorator to handle async routes."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def coro():
            try:
                return await f(*args, **kwargs)
            except Exception as e:
                logger.exception("Error in async route")
                return jsonify({"error": str(e)}), 500

        return loop.run_until_complete(coro())

    return wrapper


def error_response(error: Exception, status_code: int = 400) -> tuple[dict, int]:
    """Create a standardized error response.

    Args:
        error: The exception that occurred
        status_code: HTTP status code to return

    Returns:
        Tuple of (response dict, status code)
    """
    error_type = type(error).__name__
    return {
        "error": {
            "message": str(error),
            "type": error_type,
            "code": getattr(error, "code", None),
        }
    }, status_code


@token_status_bp.record_once
def on_register(state):
    """Reset token counter when blueprint is registered."""
    global token_counter
    token_counter = GlobalTokenCounter()


@token_status_bp.before_request
def check_session():
    """Check and initialize session state."""
    if not session.get("session_id"):
        session["session_id"] = str(uuid.uuid4())
        session["total_tokens"] = 0
        session["block_tokens"] = {}


@token_status_bp.route("/api/token-status", methods=["GET"])
@async_route
async def get_token_status():
    """Get current token status."""
    try:
        session_id = session.get("session_id")
        total_tokens = session.get("total_tokens", 0)
        block_tokens = session.get("block_tokens", {})

        return jsonify(
            {
                "session_id": session_id,
                "total_tokens": total_tokens,
                "block_tokens": block_tokens,
                "status": "success",
            }
        )
    except Exception as e:
        await error_service.notify(
            message=f"Failed to get token status: {e!s}",
            severity=ErrorSeverity.ERROR,
            source="token_status.get_token_status",
            details={"error_type": type(e).__name__},
        )
        return error_response(e, 500)


@token_status_bp.route("/api/token-status", methods=["POST"])
@async_route
async def update_token_status():
    """Update token count for a block."""
    try:
        data = request.get_json()
        if not data:
            raise ValueError("No JSON data provided")

        block_id = data.get("block_id")
        token_count = data.get("token_count")

        if not block_id:
            raise ValueError("block_id is required")

        if not isinstance(token_count, (int, float)) or token_count < 0:
            raise ValueError("token_count must be a non-negative number")

        block_tokens = session.get("block_tokens", {})
        block_tokens[block_id] = token_count
        session["block_tokens"] = block_tokens

        total_tokens = sum(block_tokens.values())
        session["total_tokens"] = total_tokens

        return jsonify(
            {
                "status": "success",
                "session_id": session["session_id"],
                "total_tokens": total_tokens,
                "block_tokens": block_tokens,
            }
        )
    except Exception as e:
        await error_service.notify(
            message=f"Failed to update token status: {e!s}",
            severity=ErrorSeverity.ERROR,
            source="token_status.update_token_status",
            details={
                "error_type": type(e).__name__,
                "block_id": block_id if "block_id" in locals() and block_id else None,
            },
        )
        return error_response(e, 500)


@token_status_bp.route("/api/token-status/reset", methods=["POST"])
@async_route
async def reset_token_status():
    """Reset token status."""
    try:
        session["session_id"] = str(uuid.uuid4())
        session["total_tokens"] = 0
        session["block_tokens"] = {}

        token_counter._blocks.clear()
        token_counter._total_tokens = 0
        token_counter._listeners.clear()
        token_counter._batch_updates.clear()
        return jsonify(
            {
                "status": "success",
                "session_id": session["session_id"],
                "total_tokens": 0,
                "block_tokens": {},
            }
        )
    except Exception as e:
        await error_service.notify(
            message=f"Failed to reset token status: {e!s}",
            severity=ErrorSeverity.ERROR,
            source="token_status.reset_token_status",
            details={"error_type": type(e).__name__},
        )
        return error_response(e, 500)


@token_status_bp.route("/api/token-status/remove", methods=["POST"])
@async_route
async def remove_block():
    """Remove a block's token count."""
    try:
        data = request.get_json()
        if not data:
            raise ValueError("No JSON data provided")

        block_id = data.get("block_id")
        if not isinstance(block_id, str) or not block_id.strip():
            raise ValueError("Invalid or missing block_id")

        block_tokens = session.get("block_tokens", {})

        if block_id in block_tokens:
            del block_tokens[block_id]

        session["block_tokens"] = block_tokens

        total_tokens = sum(block_tokens.values())
        session["total_tokens"] = total_tokens

        return jsonify(
            {
                "status": "success",
                "session_id": session.get("session_id"),
                "total_tokens": total_tokens,
                "block_tokens": block_tokens,
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error in remove_block: {e!s}")
        return jsonify({"status": "error", "message": str(e)}), 500


@token_status_bp.route("/api/token-status/batch", methods=["POST"])
@async_route
async def batch_update_token_status():
    """Batch update token counts."""
    try:
        # Get JSON data synchronously
        data = request.get_json()
        if not data:
            raise ValueError("No JSON data provided")

        updates = data.get("updates")
        if not updates:
            raise ValueError("No updates provided")

        if not isinstance(updates, dict):
            raise ValueError(
                "updates must be a dictionary mapping block IDs to token counts"
            )

        # Validate all updates before processing
        for block_id, token_count in updates.items():
            if not isinstance(token_count, (int, float)) or token_count < 0:
                raise ValueError(
                    f"Invalid token count for block {block_id}: {token_count}"
                )

        # Convert all token counts to integers
        validated_updates = {
            block_id: int(token_count) for block_id, token_count in updates.items()
        }

        block_tokens = session.get("block_tokens", {})
        for block_id, token_count in validated_updates.items():
            block_tokens[block_id] = token_count
        session["block_tokens"] = block_tokens

        # Recalculate total tokens
        total_tokens = sum(block_tokens.values())
        session["total_tokens"] = total_tokens

        return jsonify(
            {
                "status": "success",
                "session_id": session["session_id"],
                "total_tokens": total_tokens,
                "block_tokens": block_tokens,
            }
        )
    except Exception as e:
        await error_service.notify(
            message=f"Failed to batch update token status: {e!s}",
            severity=ErrorSeverity.ERROR,
            source="token_status.batch_update_token_status",
            details={"error_type": type(e).__name__},
        )
        return error_response(e, 500)


@token_status_bp.route("/api/token-status/notifications", methods=["GET"])
@async_route
async def get_notifications():
    """Get recent error notifications."""
    try:
        severity = request.args.get("severity")
        limit = request.args.get("limit", type=int)

        if severity:
            try:
                severity = ErrorSeverity(severity)
            except ValueError:
                raise ValueError(f"Invalid severity: {severity}")

        notifications = error_service.get_recent_notifications(
            limit=limit, severity=severity
        )

        return jsonify(
            {"notifications": [n.to_dict() for n in notifications], "status": "success"}
        )

    except Exception as e:
        await error_service.notify(
            message=f"Failed to get notifications: {e!s}",
            severity=ErrorSeverity.ERROR,
            source="token_status.get_notifications",
            details={"error_type": type(e).__name__},
        )
        return error_response(e, 500)


@token_status_bp.route("/api/token-status/remove-block", methods=["POST"])
@async_route
async def remove_block_from_token_counting():
    """Remove a block from token counting."""
    try:
        data = await request.get_json()
        block_id = data.get("blockId")

        if not block_id:
            return jsonify({"error": "Block ID is required"}), 400

        await token_counter.remove_block(block_id)
        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"Failed to remove block: {e!s}")
        return jsonify({"error": str(e)}), 500
