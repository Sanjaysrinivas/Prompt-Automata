from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from .db import db


class Fence(db.Model):
    """Database model for storing prompt fence blocks.

    A fence represents a named section within a prompt with specific formatting.
    Each prompt can have multiple fences, ordered by position.
    """

    __tablename__ = "fence"
    __table_args__ = (
        db.Index("idx_prompt_position", "prompt_id", "position", unique=True),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    prompt_id = db.Column(
        db.Integer, db.ForeignKey("prompt.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(100), nullable=False)
    format = db.Column(
        db.String(20),
        nullable=False,
        default="brackets",
    )
    content = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    prompt = db.relationship(
        "Prompt", back_populates="fences", foreign_keys=[prompt_id]
    )
    references = db.relationship(
        "src.app.models.reference_models.FenceReference",
        primaryjoin="Fence.id == FenceReference.fence_id",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    has_references = db.Column(db.Boolean, default=False)
    last_reference_update = db.Column(db.DateTime)
    reference_status = db.Column(db.String(50))

    def __repr__(self) -> str:
        """String representation of the Fence."""
        return f"<Fence {self.id}: {self.name} (format: {self.format}, position: {self.position})>"

    @classmethod
    def create(
        cls,
        prompt_id: int,
        name: str,
        content: str,
        format: str = "brackets",
        position: int | None = None,
    ) -> Fence | None:
        """Create a new fence for a prompt.

        Args:
            prompt_id: ID of the parent prompt
            name: Name of the fence block
            content: Content within the fence
            format: Fence format (brackets, triple_quotes, xml_tags, markdown)
            position: Position in the prompt (auto-calculated if None)

        Returns:
            The created Fence object or None if creation fails
        """
        try:
            if position is None:
                max_pos = (
                    db.session.query(db.func.max(cls.position))
                    .filter(cls.prompt_id == prompt_id)
                    .scalar()
                )
                position = (max_pos or 0) + 1

            fence = cls(
                prompt_id=prompt_id,
                name=name,
                content=content,
                format=format,
                position=position,
            )
            try:
                db.session.add(fence)
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                return None
            else:
                return fence

        except SQLAlchemyError:
            db.session.rollback()
            return None


def update_position(self, new_position: int) -> bool:
    """Update the position of this fence, shifting others as needed.

    Args:
        new_position: The new position for this fence

    Returns:
        bool: True if successful, False otherwise
    """
    old_position = self.position
    if old_position == new_position:
        return True

    temp_position = 999999
    self.position = temp_position
    db.session.flush()

    try:
        if new_position > old_position:
            db.session.query(Fence).filter(
                Fence.prompt_id == self.prompt_id,
                Fence.position > old_position,
                Fence.position <= new_position,
            ).update({Fence.position: Fence.position - 1}, synchronize_session="fetch")
        else:
            db.session.query(Fence).filter(
                Fence.prompt_id == self.prompt_id,
                Fence.position >= new_position,
                Fence.position < old_position,
            ).update({Fence.position: Fence.position + 1}, synchronize_session="fetch")

        self.position = new_position
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return False
    else:
        return True
