"""Admin routes for API token management."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import NotFound, SQLAlchemyError

from src.app.models.api_token import APIToken
from src.app.models.db import db
from src.app.utils.auth import admin_required

token_management_bp = Blueprint("token_management", __name__)


@token_management_bp.route("/api/admin/tokens", methods=["GET"])
@admin_required
def list_tokens():
    """List all API tokens."""
    tokens = APIToken.query.all()
    return jsonify(
        [
            {
                "id": token.id,
                "name": token.name,
                "service": token.service,
                "description": token.description,
                "created_at": token.created_at.isoformat(),
                "last_used": token.last_used.isoformat() if token.last_used else None,
                "is_active": token.is_active,
            }
            for token in tokens
        ]
    )


@token_management_bp.route("/api/admin/tokens", methods=["POST"])
@admin_required
def create_token():
    """Create a new API token."""
    data = request.get_json()

    if not all(k in data for k in ["name", "token", "service"]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        token = APIToken(
            name=data["name"],
            token_hash=APIToken.hash_token(data["token"]),
            service=data["service"],
            description=data.get("description"),
        )
        db.session.add(token)
        db.session.commit()

        return jsonify(
            {
                "id": token.id,
                "name": token.name,
                "service": token.service,
                "description": token.description,
                "created_at": token.created_at.isoformat(),
                "is_active": token.is_active,
            }
        ), 201

    except (SQLAlchemyError, NotFound) as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@token_management_bp.route("/api/admin/tokens/<int:token_id>", methods=["PUT"])
@admin_required
def update_token(token_id):
    """Update an API token."""
    token = APIToken.query.get_or_404(token_id)
    data = request.get_json()

    try:
        if "name" in data:
            token.name = data["name"]
        if "token" in data:
            token.token_hash = APIToken.hash_token(data["token"])
        if "service" in data:
            token.service = data["service"]
        if "description" in data:
            token.description = data["description"]
        if "is_active" in data:
            token.is_active = data["is_active"]

        token.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify(
            {
                "id": token.id,
                "name": token.name,
                "service": token.service,
                "description": token.description,
                "updated_at": token.updated_at.isoformat(),
                "is_active": token.is_active,
            }
        )

    except (SQLAlchemyError, NotFound) as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@token_management_bp.route("/api/admin/tokens/<int:token_id>", methods=["DELETE"])
@admin_required
def delete_token(token_id):
    """Delete an API token."""
    token = APIToken.query.get_or_404(token_id)

    try:
        db.session.delete(token)
        db.session.commit()
    except (SQLAlchemyError, NotFound) as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    else:
        return "", 204
