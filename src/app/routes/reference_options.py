"""API routes for getting reference options."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from src.app.models.api_endpoint import APIEndpoint
from src.app.models.reference_models import (
    PersistentVariable,
)

reference_options_bp = Blueprint("reference_options", __name__)


@reference_options_bp.route("/reference-options", methods=["GET"])
def get_reference_options():
    """Get options for the reference type."""
    ref_type = request.args.get("type")
    if not ref_type:
        return jsonify({"error": "Reference type is required"}), 400

    try:
        if ref_type == "var":
            variables = PersistentVariable.query.all()
            if not variables:
                return jsonify([{"value": "", "label": "No variables available"}])
            options = [
                {
                    "value": f"@[var:{var.name}]",
                    "label": f"{var.name} - {var.description or 'No description'}",
                }
                for var in variables
            ]
        elif ref_type == "api":
            endpoints = APIEndpoint.query.all()
            if not endpoints:
                return jsonify([{"value": "", "label": "No API endpoints available"}])
            options = [
                {
                    "value": f"@[api:{endpoint.name}]",
                    "label": f"{endpoint.name} - {endpoint.description or 'No description'}",
                }
                for endpoint in endpoints
            ]
        else:
            return jsonify({"error": "Invalid reference type"}), 400

        return jsonify(options)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
