"""Token count model for caching token counts."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from .db import db


class TokenCount(db.Model):
    """Model for storing token counts with caching metadata."""

    __tablename__ = "token_counts"

    id = Column(Integer, primary_key=True)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    token_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TokenCount(hash={self.content_hash}, count={self.token_count})>"
