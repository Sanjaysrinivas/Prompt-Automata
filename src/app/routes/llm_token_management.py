from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request, session
from litellm import completion

from src.app.auth import require_admin
from src.app.models.api_endpoint import APIEndpoint
from src.app.models.db import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

llm_token_bp = Blueprint("llm_token", __name__)

PROVIDER_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3.5-sonnet",
    "google": "gemini/gemini-1.5-pro",
}


def validate_llm_token(provider: str, token: str) -> tuple[bool, str | None]:
    """Validate an LLM API token by making a test request.

    Args:
        provider: LLM provider name ('openai', 'anthropic', or 'google')
        token: API token to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        model = PROVIDER_MODELS.get(provider)
        if not model:
            return False, f"Invalid provider: {provider}"

        messages = [{"role": "user", "content": "test"}]
        try:
            completion(model=model, messages=messages, api_key=token, max_tokens=1)
        except Exception as e:
            logger.exception("Error during LLM completion")
            return False, f"Error during LLM completion: {e}"

    except Exception as e:
        logger.exception("Error validating LLM token")
        return False, f"Error validating token: {e!s}"
    else:
        return True, None


def get_or_create_endpoint(provider: str) -> APIEndpoint:
    """Get or create an API endpoint.

    Args:
        provider: Provider name

    Returns:
        APIEndpoint object
    """
    endpoint = db.session.query(APIEndpoint).filter_by(name=provider).first()

    if not endpoint:
        endpoint = APIEndpoint(
            name=provider,
            type="llm",
            base_url="",
            auth_type="bearer",
            description=f"{provider.title()} LLM API endpoint",
        )
        db.session.add(endpoint)
        db.session.commit()

    return endpoint


def _validate_save_token_request(
    data,
) -> tuple[bool, str | tuple[str, str] | None, int | None]:
    """Validate token save request data.

    Returns:
        Tuple of (is_valid, result/error_message, status_code)
        If valid, result will be tuple of (provider, token)
    """
    if not isinstance(data, dict):
        return False, "Invalid JSON format", 400

    provider = data.get("provider")
    token = data.get("token")

    if not provider:
        return False, "Provider is required", 400
    if not token:
        return False, "Token is required", 400
    if not isinstance(token, str):
        return False, "Token must be a string", 400
    if provider not in PROVIDER_MODELS:
        return (
            False,
            f'Invalid provider. Must be one of: {", ".join(PROVIDER_MODELS.keys())}',
            400,
        )

    return True, (provider, token), None


@llm_token_bp.route("/api/llm/token", methods=["POST"])
@require_admin
def save_llm_token():
    """Save an LLM provider token in session."""
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        # Validate request data
        is_valid, result, status_code = _validate_save_token_request(request.get_json())
        if not is_valid:
            return jsonify({"error": result}), status_code

        provider, token = result

        # Validate token with provider
        is_valid, error_msg = validate_llm_token(provider, token)
        if not is_valid:
            return jsonify({"error": f"Invalid token: {error_msg}"}), 400

        # Save token
        get_or_create_endpoint(provider)
        session[f"{provider}_token"] = token
        session.modified = True
        logger.info("Token saved for provider")

        return jsonify({"message": f"{provider.title()} token saved successfully"}), 200

    except Exception:
        logger.exception("Error saving token")
        return jsonify({"error": "Internal server error"}), 500


def _validate_token_request(data) -> tuple[bool, str | None, int | None]:
    """Validate token deletion request data.

    Returns:
        Tuple of (is_valid, error_message, status_code)
    """
    if not isinstance(data, dict):
        return False, "Invalid JSON format", 400

    provider = data.get("provider")
    if not provider:
        return False, "Provider is required", 400
    if provider not in PROVIDER_MODELS:
        return (
            False,
            f'Invalid provider. Must be one of: {", ".join(PROVIDER_MODELS.keys())}',
            400,
        )

    return True, provider, None


@llm_token_bp.route("/api/llm/token", methods=["DELETE"])
@require_admin
def delete_llm_token():
    """Delete an LLM provider token from session."""
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        is_valid, result, status_code = _validate_token_request(request.get_json())
        if not is_valid:
            return jsonify({"error": result}), status_code

        provider = result
        token_key = f"{provider}_token"

        if token_key in session:
            session.pop(token_key)
            logger.info("Token removed for provider")
            return jsonify(
                {"message": f"{provider.title()} token removed successfully"}
            )

        return jsonify({"error": "No token found"}), 404

    except Exception:
        logger.exception("Error removing token")
        return jsonify({"error": "Internal server error"}), 500


@llm_token_bp.route("/api/llm/token/<provider>", methods=["GET"])
@require_admin
def get_llm_token(provider: str):
    """Get a stored LLM provider token."""
    if provider not in PROVIDER_MODELS:
        return jsonify(
            {
                "error": f'Invalid provider. Must be one of: {", ".join(PROVIDER_MODELS.keys())}'
            }
        ), 400

    token = session.get(f"{provider}_token")
    if token:
        return jsonify({"token": token})
    return jsonify({"error": "No token found"}), 404


@llm_token_bp.route("/api/llm/providers", methods=["GET"])
def list_providers():
    """List available LLM providers and their models."""
    return jsonify(
        {
            "providers": {
                provider: {
                    "model": model,
                    "has_token": f"{provider}_token" in session,
                }
                for provider, model in PROVIDER_MODELS.items()
            }
        }
    )


@llm_token_bp.route("/api/llm/token/status", methods=["GET"])
@require_admin
def get_token_status():
    """Get the status of all LLM provider tokens."""
    try:
        status = {}
        for provider in PROVIDER_MODELS:
            token = session.get(f"{provider}_token")
            status[provider] = token is not None
        return jsonify(status)
    except Exception as e:
        logger.exception("Error getting token status")
        return jsonify({"error": str(e)}), 500
