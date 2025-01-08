from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from src.app.services.llm_service import LLMService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


bp = Blueprint("llm_completion", __name__)


llm_service = LLMService()


@bp.route("/api/llm/completion", methods=["POST"])
def generate_completion():
    """Generate completion using the specified provider."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        provider = data.get("provider")
        prompt = data.get("prompt")

        if not provider:
            return jsonify({"error": "Provider not specified"}), 400
        if not prompt:
            return jsonify({"error": "Prompt not provided"}), 400

        response = llm_service.generate_completion(provider, prompt)
        return jsonify(response)

    except ValueError as e:
        logger.exception("Validation error")
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Error generating completion")
        return jsonify({"error": "Internal server error"}), 500
