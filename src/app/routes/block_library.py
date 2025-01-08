"""Routes for block library management."""

from __future__ import annotations

import logging
from http import HTTPStatus

from flask import Blueprint, jsonify, request
from sqlalchemy import select
from werkzeug.exceptions import BadRequest, NotFound

from src.app.models.block_library import BlockLibrary
from src.app.models.db import db
from src.app.validators.fence_validators import (
    BlockContentValidator,
    FenceContentValidator,
)

logger = logging.getLogger(__name__)

block_library_bp = Blueprint("block_library", __name__, url_prefix="/api/block-library")

block_validator = BlockContentValidator()
fence_validator = FenceContentValidator()


def _raise_error(exception, message):
    """Helper function to raise exceptions with a message."""
    raise exception(message)


def _get_block_or_404(block_id):
    """Get block by ID or raise 404."""
    result = db.session.get(BlockLibrary, block_id)
    if not result:
        _raise_error(NotFound, f"Block {block_id} not found")
    return result


@block_library_bp.route("", methods=["POST"])
def save_block():
    """Save a block to the library.

    Expected JSON body:
    {
        "name": "string",
        "description": "string" (optional),
        "content": "string",
        "format": "string",
        "metadata": {} (optional)
    }
    """
    try:
        data = request.get_json()
        if not data:
            _raise_error(BadRequest, "No data provided")

        required_fields = ["name", "content", "format"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            _raise_error(
                BadRequest, f"Missing required fields: {', '.join(missing_fields)}"
            )

        if not data["name"].strip():
            _raise_error(BadRequest, "Block name cannot be empty")

        if not data["content"].strip():
            _raise_error(BadRequest, "Block content cannot be empty")

        block = BlockLibrary.from_dict(data)
        db.session.add(block)
        db.session.commit()

        return jsonify(block.to_dict()), HTTPStatus.CREATED

    except BadRequest as e:
        return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.exception("Error saving block")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@block_library_bp.route("", methods=["GET"])
def list_blocks():
    """List all blocks in the library."""
    try:
        stmt = select(BlockLibrary).order_by(BlockLibrary.created_at.desc())
        blocks = db.session.execute(stmt).scalars().all()
        return jsonify([block.to_dict() for block in blocks])

    except Exception as e:
        logger.exception("Error listing blocks")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@block_library_bp.route("/<block_id>", methods=["GET"])
def get_block(block_id):
    """Get a specific block from the library."""
    try:
        block = _get_block_or_404(block_id)
        return jsonify(block.to_dict())

    except NotFound as e:
        return jsonify({"error": str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        logger.exception("Error getting block")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@block_library_bp.route("/<block_id>", methods=["DELETE"])
def delete_block(block_id):
    """Delete a block from the library."""
    try:
        block = _get_block_or_404(block_id)
        db.session.delete(block)
        db.session.commit()

    except NotFound as e:
        return jsonify({"error": str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        logger.exception("Error deleting block")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    else:
        return "", HTTPStatus.NO_CONTENT


@block_library_bp.route("/export", methods=["POST"])
def export_blocks():
    """Export selected blocks from the library.

    Expected JSON body:
    {
        "block_ids": [string]  # List of block IDs to export
    }
    """
    try:
        data = request.get_json()
        if not data or "block_ids" not in data:
            _raise_error(BadRequest, "No block IDs provided")

        blocks = []
        for block_id in data["block_ids"]:
            try:
                block = _get_block_or_404(block_id)
                blocks.append(block.to_dict())
            except NotFound:
                continue

        return jsonify(blocks)

    except BadRequest as e:
        return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.exception("Error exporting blocks")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@block_library_bp.route("/import", methods=["POST"])
def import_blocks():
    """Import blocks into the library.

    Expected JSON body:
    {
        "blocks": [{
            "name": "string",
            "description": "string" (optional),
            "content": "string",
            "format": "string",
            "metadata": {} (optional)
        }]
    }
    """
    try:
        data = request.get_json()
        if not data or "blocks" not in data:
            _raise_error(BadRequest, "No blocks provided")

        imported_blocks = []
        for block_data in data["blocks"]:
            required_fields = ["name", "content", "format"]
            missing_fields = [
                field for field in required_fields if field not in block_data
            ]
            if missing_fields:
                _raise_error(
                    BadRequest, f"Missing required fields: {', '.join(missing_fields)}"
                )

            # Create and save the block
            block = BlockLibrary.from_dict(block_data)
            db.session.add(block)
            imported_blocks.append(block)

        db.session.commit()
        return jsonify(
            [block.to_dict() for block in imported_blocks]
        ), HTTPStatus.CREATED

    except BadRequest as e:
        return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.exception("Error importing blocks")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
