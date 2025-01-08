"""Models for the block library system."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.app.models.base import Base


class BlockLibrary(Base):
    """Model for storing reusable fence blocks."""

    __tablename__ = "block_library"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(String(50), nullable=False)
    block_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=True, default={}
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert block to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "format": self.format,
            "metadata": self.block_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> BlockLibrary:
        """Create block from dictionary."""
        return BlockLibrary(
            name=data["name"],
            description=data.get("description"),
            content=data["content"],
            format=data["format"],
            block_metadata=data.get("metadata", {}),
        )
