"""Service layer for handling prompt operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from src.app.models.db import db
from src.app.models.fence import Fence
from src.app.models.prompt import Prompt

if TYPE_CHECKING:
    from collections.abc import Sequence


class PromptServiceError(Exception):
    """Base exception for prompt service errors."""


class PromptNotFoundError(PromptServiceError):
    """Raised when a prompt is not found."""


class PromptOperationError(PromptServiceError):
    """Raised when a prompt operation fails."""


@dataclass
class PromptCreate:
    """Data class for prompt creation parameters."""

    title: str
    content: str
    description: str | None = None
    tags: list[str] | None = None
    category: str | None = None
    is_template: bool = False
    metadata: dict | None = None


class PromptService:
    """Service class for handling prompt-related operations."""

    @staticmethod
    async def create_prompt(
        title: str,
        content: str = "",
        *,
        description: str | None = None,
        tags: list[str] | None = None,
        is_template: bool = False,
        provider: str | None = None,
        model: str | None = None,
        fences: list[dict] | None = None,
    ) -> tuple[dict, str | None]:
        """Create a new prompt."""
        try:
            print(f"[PromptService] Creating prompt with title: {title}")
            print(f"[PromptService] Description: {description}")
            print(f"[PromptService] Tags: {tags}")
            print(f"[PromptService] Is template: {is_template}")
            print(f"[PromptService] Provider: {provider}")
            print(f"[PromptService] Model: {model}")
            print(f"[PromptService] Number of fences: {len(fences) if fences else 0}")

            prompt = Prompt(
                title=title,
                content=content,
                description=description or "",
                tags=",".join(tags) if tags else "",
                is_template=is_template,
                provider=provider,
                model=model,
            )
            db.session.add(prompt)
            db.session.flush()

            print(f"[PromptService] Created prompt with ID: {prompt.id}")

            if fences:
                print(f"[PromptService] Creating {len(fences)} fences")
                for i, fence_data in enumerate(fences, 1):
                    print(f"[PromptService] Creating fence {i}/{len(fences)}")
                    print(f"[PromptService] Fence data: {fence_data}")

                    fence = Fence(
                        prompt_id=prompt.id,
                        name=fence_data["name"],
                        format=fence_data["format"],
                        content=fence_data["content"],
                        position=fence_data.get("position", 0),
                    )
                    db.session.add(fence)
                    print(f"[PromptService] Created fence with ID: {fence.id}")

                    has_references = "@[" in fence_data["content"]
                    print(f"[PromptService] Fence has references: {has_references}")

            db.session.commit()
            print("[PromptService] Successfully committed changes to database")

            prompt_dict = prompt.to_dict()
            print(f"[PromptService] Returning prompt dict: {prompt_dict}")

            return prompt_dict, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Failed to create prompt: {e!s}"
            print(f"[PromptService] Error: {error_msg}")
            return {}, error_msg

    @staticmethod
    def get_prompt(prompt_id: int) -> tuple[dict | None, str | None]:
        """Get a prompt by ID.

        Args:
            prompt_id: ID of the prompt to retrieve

        Returns:
            Tuple of (prompt_dict, error_message)

        Raises:
            PromptNotFoundError: If the prompt is not found
        """
        try:
            prompt = Prompt.query.get(prompt_id)
            if prompt is None:
                msg = f"Prompt with ID {prompt_id} not found"
                raise PromptNotFoundError(msg)
        except SQLAlchemyError as err:
            return None, f"Failed to retrieve prompt: {err!s}"
        else:
            return prompt.to_dict(), None

    @staticmethod
    def get_all_prompts(*, template_only: bool = False) -> list[dict]:
        """Get all prompts.

        Args:
            template_only: Whether to only return templates

        Returns:
            List of prompt dictionaries

        Raises:
            PromptOperationError: If there is an error retrieving prompts
        """
        try:
            query = Prompt.query
            if template_only:
                query = query.filter_by(is_template=True)
            prompts = query.order_by(Prompt.created_at.desc()).all()
            return [prompt.to_dict() for prompt in prompts]
        except SQLAlchemyError as err:
            msg = f"Failed to retrieve prompts: {err!s}"
            raise PromptOperationError(msg) from err

    @staticmethod
    def update_prompt(prompt_id: int, **kwargs) -> tuple[dict | None, str | None]:
        """Update a prompt.

        Args:
            prompt_id: ID of the prompt to update
            **kwargs: Fields to update

        Returns:
            Tuple of (prompt_dict, error_message)
        """
        try:
            prompt = Prompt.query.get(prompt_id)
            if prompt is None:
                msg = f"Prompt with ID {prompt_id} not found"
                raise PromptNotFoundError(msg)

            if "tags" in kwargs and isinstance(kwargs["tags"], list):
                kwargs["tags"] = ",".join(kwargs["tags"])

            if "title" in kwargs and not kwargs["title"]:
                return None, "Title cannot be empty"

            if "fences" in kwargs:
                Fence.query.filter_by(prompt_id=prompt_id).delete()

                for fence_data in kwargs["fences"]:
                    fence = Fence(
                        prompt_id=prompt_id,
                        name=fence_data["name"],
                        format=fence_data["format"],
                        content=fence_data["content"],
                        position=fence_data["position"],
                    )
                    db.session.add(fence)

            for key, value in kwargs.items():
                if hasattr(prompt, key) and key != "fences":
                    setattr(prompt, key, value)

            db.session.commit()
            return prompt.to_dict(), None

        except PromptNotFoundError as err:
            return None, str(err)
        except SQLAlchemyError as err:
            db.session.rollback()
            return None, f"Failed to update prompt: {err!s}"

    @staticmethod
    def delete_prompt(prompt_id: int) -> tuple[bool, str | None]:
        """Delete a prompt.

        Args:
            prompt_id: ID of the prompt to delete

        Returns:
            Tuple of (success, error_message)

        Raises:
            PromptNotFoundError: If the prompt is not found
        """
        try:
            prompt = Prompt.query.get(prompt_id)
            if prompt is None:
                msg = f"Prompt with ID {prompt_id} not found"
                raise PromptNotFoundError(msg)
            prompt.delete()
        except SQLAlchemyError as err:
            return False, f"Failed to delete prompt: {err!s}"
        else:
            return True, None

    @staticmethod
    def search_prompts(
        query: str = "",
        tags: Sequence[str] | None = None,
        *,
        template_only: bool = False,
    ) -> list[dict]:
        """Search prompts by title, content, tags, or fence content.

        Args:
            query: Search string for title, content, and fence content
            tags: List of tags to filter by
            template_only: Whether to only return templates

        Returns:
            List of matching prompt dictionaries

        Raises:
            PromptOperationError: If there is an error searching prompts
        """
        try:
            base_query = Prompt.query

            if template_only:
                base_query = base_query.filter_by(is_template=template_only)

            if query:
                base_query = (
                    base_query.join(Fence, isouter=True)
                    .filter(
                        or_(
                            Prompt.title.ilike(f"%{query}%"),
                            Prompt.content.ilike(f"%{query}%"),
                            Prompt.description.ilike(f"%{query}%"),
                            Fence.content.ilike(f"%{query}%"),
                        )
                    )
                    .distinct()
                )

            if tags:
                for tag in tags:
                    base_query = base_query.filter(Prompt.tags.ilike(f"%{tag}%"))

            prompts = base_query.order_by(Prompt.created_at.desc()).all()
        except SQLAlchemyError as err:
            msg = f"Failed to search prompts: {err!s}"
            raise PromptOperationError(msg) from err
        else:
            return [prompt.to_dict() for prompt in prompts]
