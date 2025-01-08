"""Base model class for SQLAlchemy models."""

from __future__ import annotations

from src.app.models.db import db

Base = db.Model
