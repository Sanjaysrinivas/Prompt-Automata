from __future__ import annotations

from datetime import datetime

from .db import db


class AllowedDirectory(db.Model):
    """Model for allowed directories."""

    __tablename__ = "allowed_directory"

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(500), unique=True, nullable=False)
    description = db.Column(db.String(500))
    is_recursive = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<AllowedDirectory {self.path}>"
