"""API endpoint model for storing API configurations."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from sqlalchemy import JSON
from sqlalchemy.orm import relationship

from .db import db


class APIEndpoint(db.Model):
    """Model for storing API endpoint configurations."""

    __tablename__ = "api_endpoint"
    __table_args__: ClassVar[dict[str, bool]] = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    base_url = db.Column(db.String(500), nullable=False)
    auth_type = db.Column(db.String(50))
    auth_token = db.Column(db.String(500))
    headers = db.Column(JSON)
    rate_limit = db.Column(db.Integer)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tokens = relationship(
        "APIToken", back_populates="endpoint", cascade="all, delete-orphan"
    )

    def __repr__(self):
        """String representation of the API endpoint."""
        return f"<APIEndpoint name='{self.name}' type='{self.type}'>"
