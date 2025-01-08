from __future__ import annotations

from datetime import datetime

from .db import db


class PersistentVariable(db.Model):
    """Model for persistent variables."""

    __tablename__ = "persistent_variable"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<PersistentVariable {self.name}>"
