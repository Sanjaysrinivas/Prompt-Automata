"""API token model for secure token storage."""

from __future__ import annotations

import logging
from datetime import datetime

from src.app.models.db import db

logger = logging.getLogger(__name__)


class APIToken(db.Model):
    """Model for storing API tokens."""

    __tablename__ = "api_tokens"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    token_hash = db.Column(db.String(255), nullable=False)
    encrypted_token = db.Column(db.String(255))
    service = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(500))
    endpoint_id = db.Column(db.Integer, db.ForeignKey("api_endpoint.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_used = db.Column(db.DateTime)
    last_validated = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    is_valid = db.Column(db.Boolean, default=False)

    # Relationships
    endpoint = db.relationship("APIEndpoint", back_populates="tokens")

    @property
    def token(self):
        """Get decrypted token."""
        if not self.encrypted_token:
            return None
        # TODO: Implement decryption
        return self.encrypted_token

    @token.setter
    def token(self, value):
        """Set encrypted token and hash."""
        if value is None:
            self.encrypted_token = None
            self.token_hash = None
            return
        # TODO: Implement encryption
        self.encrypted_token = value
        self.token_hash = value  # For now, just store the raw value

    def __init__(self, **kwargs):
        """Initialize the token."""
        if "token" in kwargs:
            token = kwargs.pop("token")
            super().__init__(**kwargs)
            self.token = token
        else:
            super().__init__(**kwargs)

    def __repr__(self):
        """Return string representation."""
        return f"<APIToken {self.name}>"
