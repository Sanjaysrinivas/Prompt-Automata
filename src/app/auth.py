"""Authentication utilities for the application."""

from __future__ import annotations

import logging
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import current_app, jsonify, request, session

logger = logging.getLogger(__name__)


def cleanup_session():
    """Clean up sensitive data from session."""
    try:
        sensitive_keys = [
            "github_token",
            "openai_token",
            "anthropic_token",
            "google_token",
            "last_activity",
            "initialized",
            "session_id",
            "total_tokens",
            "block_tokens",
            "admin_token",
        ]

        for key in sensitive_keys:
            if key in session:
                session.pop(key, None)
                logger.debug("Cleaned up %s from session", key)

        session.modified = True

        session.clear()

        if hasattr(session, "save_session"):
            session.save_session()

        logger.info("Session cleared completely")

    except Exception:
        logger.exception("Error during session cleanup")
        with suppress(Exception):
            session.clear()


def check_session_expiry():
    """Check if the session has expired and needs cleanup.

    Returns:
        bool: True if session was expired and cleaned up, False otherwise
    """
    if not session.get("initialized"):
        session["initialized"] = True
        session["last_activity"] = datetime.now(tz=timezone.utc).isoformat()
        logger.debug("New session initialized")
        return False

    last_activity = session.get("last_activity")

    if not last_activity:
        logger.warning("No last activity timestamp found, cleaning up session")
        cleanup_session()
        return True

    try:
        last_activity = datetime.fromisoformat(last_activity)
        if datetime.now(tz=timezone.utc) - last_activity > timedelta(hours=1):
            logger.info("Session expired, cleaning up")
            cleanup_session()
        else:
            session["last_activity"] = datetime.now(tz=timezone.utc).isoformat()
            session.modified = True
            return False
    except (ValueError, TypeError):
        logger.exception("Error parsing last activity timestamp")
        cleanup_session()
        return True


def require_admin(f):
    """Decorator to require admin token for a route."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_token = current_app.config.get("ADMIN_TOKEN")
        if not admin_token:
            return jsonify({"error": "Admin token not configured"}), 500

        auth_header = request.headers.get("Authorization")
        admin_header = request.headers.get("X-Admin-Token")

        token = None
        if auth_header:
            try:
                token_type, token = auth_header.split(" ", 1)
                if token_type.lower() != "bearer":
                    return jsonify({"error": "Invalid token type"}), 401
            except ValueError:
                return jsonify({"error": "Invalid authorization header"}), 401

        if not token and admin_header:
            token = admin_header

        if not token:
            return jsonify({"error": "No authorization header"}), 401

        if token != admin_token:
            return jsonify({"error": "Invalid admin token"}), 401

        return f(*args, **kwargs)

    return decorated_function
