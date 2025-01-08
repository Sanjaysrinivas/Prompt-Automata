"""Routes for fence management within prompts."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from flask import Blueprint, jsonify, request
from sqlalchemy import select
from werkzeug.exceptions import BadRequest, NotFound, SQLAlchemyError

from src.app.models.db import db
from src.app.models.fence import Fence
from src.app.models.prompt import Prompt
from src.app.validators.base import ValidationError
from src.app.validators.fence_validators import (
    BlockContentValidator,
    FenceContentValidator,
    FileReferenceValidator,
    VariableReferenceValidator,
)

fences_bp = Blueprint("fences", __name__, url_prefix="/fences")


def _get_prompt_or_404(prompt_id: int) -> Prompt:
    """Get prompt by ID or raise 404."""
    result = db.session.get(Prompt, prompt_id)
    if not result:
        msg = f"Prompt {prompt_id} not found"
        raise NotFound(msg)
    return result


def _get_fence_or_404(fence_id: int, prompt_id: int) -> Fence:
    """Get fence by ID and prompt_id or raise 404."""
    fence = db.session.get(Fence, fence_id)
    if not fence or fence.prompt_id != prompt_id:
        msg = f"Fence {fence_id} not found in prompt {prompt_id}"
        raise NotFound(msg)
    return fence


def _raise_bad_request(message: str, original_error: Exception | None = None) -> None:
    """Raise BadRequest with consistent error handling."""
    raise BadRequest(message) from original_error


@fences_bp.route("/prompts/<int:prompt_id>/fences", methods=["POST"])
def create_fence(prompt_id: int) -> tuple[dict[str, Any], int]:
    """Create a new fence in a prompt.

    Expected JSON body:
    {
        "name": "string",
        "format": "string",
        "content": "string",
        "position": "integer" (optional)
    }
    """
    _get_prompt_or_404(prompt_id)
    data = request.get_json()

    if not data:
        _raise_bad_request("No data provided")

    required_fields = ["name", "format", "content"]
    if not all(field in data for field in required_fields):
        _raise_bad_request(f"Missing required fields: {required_fields}")

    try:
        FenceContentValidator().validate(data.get("content"))
        BlockContentValidator().validate(data.get("content"))

        if "{{file:" in data.get("content", ""):
            FileReferenceValidator().validate(data.get("content"))

        if "{{var:" in data.get("content", ""):
            VariableReferenceValidator().validate(data.get("content"))

    except ValidationError as e:
        return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

    max_position = (
        db.session.scalar(
            select(db.func.max(Fence.position)).where(Fence.prompt_id == prompt_id)
        )
        or -1
    )

    target_position = data.get("position")
    if target_position is not None:
        if target_position < 0:
            _raise_bad_request("Position cannot be negative")

        target_position = min(target_position, max_position + 1)

        db.session.execute(
            db.update(Fence)
            .where(Fence.prompt_id == prompt_id, Fence.position >= target_position)
            .values(position=Fence.position + 1)
        )
    else:
        target_position = max_position + 1

    try:
        fence = Fence(
            prompt_id=prompt_id,
            name=data["name"],
            format=data["format"],
            content=data["content"],
            position=target_position,
        )
        db.session.add(fence)
        db.session.commit()
    except (SQLAlchemyError, NotFound) as e:
        db.session.rollback()
        _raise_bad_request("Failed to create fence", e)

    return jsonify(fence.to_dict()), HTTPStatus.CREATED


@fences_bp.route("/prompts/<int:prompt_id>/fences", methods=["GET"])
def list_fences(prompt_id: int) -> tuple[dict[str, Any], int]:
    """List all fences for a prompt."""
    _get_prompt_or_404(prompt_id)

    fences = db.session.scalars(
        select(Fence).where(Fence.prompt_id == prompt_id).order_by(Fence.position)
    ).all()

    return jsonify(
        {
            "fences": [
                {
                    "id": fence.id,
                    "name": fence.name,
                    "format": fence.format,
                    "content": fence.content,
                    "position": fence.position,
                }
                for fence in fences
            ]
        }
    ), HTTPStatus.OK


@fences_bp.route("/prompts/<int:prompt_id>/fences/<int:fence_id>", methods=["PUT"])
def update_fence(prompt_id: int, fence_id: int) -> tuple[dict[str, Any], int]:
    """Update an existing fence.

    Expected JSON body:
    {
        "name": "string" (optional),
        "content": "string" (optional)
    }
    Note: format cannot be changed after creation
    """
    fence = _get_fence_or_404(fence_id, prompt_id)
    data = request.get_json()

    if not data:
        _raise_bad_request("No data provided")

    if "content" in data:
        try:
            FenceContentValidator().validate(data["content"])
            BlockContentValidator().validate(data["content"])

            if "{{file:" in data["content"]:
                FileReferenceValidator().validate(data["content"])

            if "{{var:" in data["content"]:
                VariableReferenceValidator().validate(data["content"])

        except ValidationError as e:
            return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

    if "name" in data:
        fence.name = data["name"]
    if "content" in data:
        fence.content = data["content"]

    try:
        db.session.commit()
    except (SQLAlchemyError, NotFound) as e:
        db.session.rollback()
        _raise_bad_request("Failed to update fence", e)

    return jsonify(fence.to_dict()), HTTPStatus.OK


@fences_bp.route("/prompts/<int:prompt_id>/fences/<int:fence_id>", methods=["DELETE"])
def delete_fence(prompt_id: int, fence_id: int) -> tuple[dict[str, Any], int]:
    """Delete a fence from a prompt."""
    fence = _get_fence_or_404(fence_id, prompt_id)

    try:
        db.session.delete(fence)
        db.session.commit()
    except (SQLAlchemyError, NotFound) as e:
        db.session.rollback()
        _raise_bad_request("Failed to delete fence", e)

    return jsonify({"message": "Fence deleted successfully"}), HTTPStatus.OK


def _validate_reorder_request(data: dict | None) -> list[dict]:
    """Validate reorder request data.

    Args:
        data: Request data to validate

    Returns:
        List of validated order items

    Raises:
        BadRequest: If validation fails
    """
    if not data or "order" not in data:
        _raise_bad_request("No order data provided")

    order_data = data["order"]
    if not isinstance(order_data, list):
        _raise_bad_request("Order must be a list")

    if not order_data:
        _raise_bad_request("Order list cannot be empty")

    return order_data


def _validate_order_items(order_items: list[dict]) -> dict[int, int]:
    """Validate order items and return position mapping.

    Args:
        order_items: List of order items to validate
        prompt_id: ID of the prompt

    Returns:
        Dictionary mapping fence IDs to positions

    Raises:
        BadRequest: If validation fails
    """
    positions = {}
    seen_positions = set()

    for item in order_items:
        if not isinstance(item, dict):
            _raise_bad_request("Each order item must be an object")

        if "id" not in item or "position" not in item:
            _raise_bad_request("Each order item must have 'id' and 'position'")

        fence_id = item["id"]
        position = item["position"]

        if not isinstance(position, int) or position < 0:
            _raise_bad_request("Position must be a non-negative integer")

        if position in seen_positions:
            _raise_bad_request("Duplicate position found")

        seen_positions.add(position)
        positions[fence_id] = position

    return positions


@fences_bp.route("/prompts/<int:prompt_id>/fences/reorder", methods=["POST"])
def reorder_fences(prompt_id: int) -> tuple[dict[str, Any], int]:
    """Reorder fences within a prompt."""
    try:
        # Validate request data
        data = request.get_json()
        order_items = _validate_reorder_request(data)
        positions = _validate_order_items(order_items)

        # Get all fences for this prompt
        fences = db.session.scalars(
            select(Fence).where(Fence.prompt_id == prompt_id)
        ).all()

        # Update positions
        fence_ids = {fence.id for fence in fences}
        for fence_id, position in positions.items():
            if fence_id not in fence_ids:
                _raise_bad_request(f"Fence {fence_id} not found in prompt {prompt_id}")

            fence = next(f for f in fences if f.id == fence_id)
            fence.position = position

        db.session.commit()
        return jsonify({"message": "Fences reordered successfully"}), HTTPStatus.OK

    except (SQLAlchemyError, NotFound) as e:
        db.session.rollback()
        _raise_bad_request("Failed to reorder fences", e)
