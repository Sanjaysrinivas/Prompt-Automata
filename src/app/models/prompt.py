"""Prompt model definition for database storage."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from sqlalchemy.exc import SQLAlchemyError

from .db import db


class Prompt(db.Model):
    """Database model for storing prompts and their metadata."""

    __tablename__ = "prompt"
    __table_args__: ClassVar[dict[str, bool]] = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True)
    fence_format = db.Column(db.String(50), nullable=False, default="curly")
    tags = db.Column(db.String(200), nullable=True)
    is_template = db.Column(db.Boolean, default=False)
    provider = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    git_ref = db.Column(db.String(40))

    fences = db.relationship(
        "Fence",
        back_populates="prompt",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="Fence.position",
    )

    @classmethod
    def create(cls, title: str, content: str, **kwargs) -> Prompt | None:
        """Create a new prompt."""
        try:
            prompt = cls(title=title, content=content, **kwargs)
            db.session.add(prompt)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            return None
        else:
            return prompt

    @classmethod
    def get_by_id(cls, prompt_id: int) -> Prompt | None:
        """Get a prompt by its ID."""
        return cls.query.get(prompt_id)

    @classmethod
    def get_all(cls, *, template_only: bool = False) -> list[Prompt]:
        """Get all prompts, optionally filtered by template status."""
        query = cls.query
        if template_only:
            query = query.filter_by(is_template=True)
        return query.order_by(cls.created_at.desc()).all()

    def update(self, **kwargs) -> bool:
        """Update prompt attributes."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            return False
        else:
            return True

    def delete(self) -> bool:
        """Delete the prompt."""
        try:
            db.session.delete(self)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            return False
        else:
            return True

    def to_dict(self) -> dict:
        """Convert prompt to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "description": self.description or "",
            "tags": self.tags.split(",") if self.tags else [],
            "is_template": self.is_template,
            "provider": self.provider,
            "model": self.model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "fences": [
                {
                    "id": fence.id,
                    "name": fence.name,
                    "format": fence.format,
                    "content": fence.content,
                    "position": fence.position,
                }
                for fence in sorted(self.fences, key=lambda f: f.position)
            ]
            if self.fences
            else [],
        }

    def __repr__(self) -> str:
        """String representation of the Prompt model."""
        return f"<Prompt {self.title}>"
