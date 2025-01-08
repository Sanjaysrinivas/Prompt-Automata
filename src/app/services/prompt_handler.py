"""Service for handling prompt operations."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import ClassVar

from flask import current_app

from src.app import db
from src.app.models.prompt import Prompt
from src.app.services.git_handler import GitHandler

# Configure logging
logging.basicConfig(level=logging.INFO)


class FenceFormat(Enum):
    """Available fencing formats."""

    TRIPLE_QUOTES = "triple_quotes"  # '''text'''
    CURLY_BRACES = "curly_braces"  # {text}
    XML_TAGS = "xml_tags"  # <tag>text</tag>
    MARKDOWN = "markdown"  # ```text```


@dataclass
class FenceConfig:
    """Configuration for a fence format."""

    start: str
    end: str
    indent: str = "    "  # Default 4-space indent
    newlines: bool = True  # Whether to add newlines around content


class PromptHandler:
    """Handler for prompt-related operations."""

    FILE_REFERENCE_PATTERN = r"@\[(.*?)\]"

    # Define fence formats
    FENCE_FORMATS: ClassVar[dict[FenceFormat, FenceConfig]] = {
        FenceFormat.TRIPLE_QUOTES: FenceConfig("'''", "'''"),
        FenceFormat.CURLY_BRACES: FenceConfig("{", "}"),
        FenceFormat.XML_TAGS: FenceConfig("<{tag}>", "</{tag}>"),
        FenceFormat.MARKDOWN: FenceConfig("```{language}", "```"),
    }

    def __init__(self) -> None:
        """Initialize the prompt handler with Git integration."""
        self.git_handler = GitHandler()
        workspace = current_app.config.get("WORKSPACE_PATH", Path.cwd())
        self.workspace = Path(workspace).resolve()
        logging.info(f"PromptHandler initialized with workspace: {self.workspace}")

    def _raise_prompt_not_found(self, prompt_id: int) -> None:
        """Raise ValueError when prompt is not found."""
        msg = f"Prompt with ID {prompt_id} not found"
        raise ValueError(msg)

    def _raise_missing_fields(self) -> None:
        """Raise ValueError when required fields are missing."""
        msg = "Title and content are required"
        raise ValueError(msg)

    def resolve_file_reference(self, file_path: str) -> str:
        """Resolve a file reference to its content."""
        try:
            logging.info(f"Resolving file: {file_path}")
            target_path = Path(file_path)
            logging.info(f"Target path: {target_path}")

            if not target_path.is_file():
                logging.error(f"File not found: {target_path}")
                return f"Error: File {file_path} not found"

            try:
                return target_path.read_text(encoding="utf-8")
            except OSError as e:
                logging.exception(f"Error reading file {file_path}: {e}")
                return f"Error: Could not read file {file_path}"

        except Exception as e:
            logging.exception(f"Error resolving file {file_path}: {e}")
            return f"Error: Could not resolve file {file_path}"

    def apply_fence(
        self,
        content: str,
        fence_format: FenceFormat,
        tag: str = "context",
        language: str = "",
    ) -> str:
        """Apply fencing to content using the specified format."""
        if not content:
            return ""

        config = self.FENCE_FORMATS[fence_format]

        # Indent content for better readability
        lines = content.splitlines()
        indented_lines = [config.indent + line if line else line for line in lines]
        indented_content = "\n".join(indented_lines)

        if fence_format == FenceFormat.XML_TAGS:
            # For XML tags, use the tag name as the fence name
            # and wrap the content with corresponding XML tags
            return f"\n<{tag}>\n{indented_content}\n</{tag}>\n"
        # For other formats (triple quotes, curly braces, markdown),
        # show the fence name first, then apply fences to content only
        parts = [tag]  # Start with the fence name

        if fence_format == FenceFormat.MARKDOWN:
            start = config.start.format(language=language)
            end = config.end
        else:
            start = config.start
            end = config.end

        # Add the fenced content
        parts.extend(["", start, indented_content, end, ""])

        return "\n".join(parts)

    def process_prompt(
        self,
        content: str,
        fence_format: FenceFormat | None = None,
        *,
        resolve_files: bool = True,
        apply_fences: bool = True,
        fence_name: str = "context",  # Default value for fence_name
    ) -> str:
        """Process a prompt by resolving file references and applying fencing."""
        if apply_fences and fence_format is None:
            fence_format = FenceFormat.XML_TAGS

        try:
            # Check if content already has XML tags
            xml_pattern = r"<[^>]+>[^<]*</[^>]+>"
            has_xml_tags = bool(
                re.search(xml_pattern, content, re.MULTILINE | re.DOTALL)
            )

            # Try to parse the content as JSON containing name and content
            import json

            try:
                data = json.loads(content)
                if isinstance(data, dict) and "name" in data and "content" in data:
                    fence_name = data["name"]
                    content = data["content"]
            except (json.JSONDecodeError, AttributeError):
                # If parsing fails, use content as is
                pass

            if resolve_files:

                def replace_reference(match: re.Match) -> str:
                    file_path = match.group(1)
                    file_content = self.resolve_file_reference(file_path)
                    return (
                        self.apply_fence(
                            file_content, fence_format, tag=fence_name, language=""
                        )
                        if apply_fences
                        else file_content
                    )

                content = re.sub(
                    self.FILE_REFERENCE_PATTERN, replace_reference, content
                )

            # Only apply fence if content doesn't already have XML tags
            if has_xml_tags:
                return content
            return (
                self.apply_fence(content, fence_format, tag=fence_name)
                if apply_fences
                else content
            )
        except Exception as e:
            logging.exception(f"Error processing prompt: {e}")
            raise

    def save_prompt(
        self, title: str, content: str, prompt_id: int | None = None
    ) -> Prompt:
        """Save or update a prompt with Git metadata."""
        try:
            logging.info(f"Saving prompt - Title: {title}, ID: {prompt_id}")

            if not title or not content:
                self._raise_missing_fields()

            git_ref = None
            if self.git_handler.repo:
                git_ref = self.git_handler.get_current_commit()

            if prompt_id:
                prompt = Prompt.query.get(prompt_id)
                if not prompt:
                    self._raise_prompt_not_found(prompt_id)
                prompt.title = title
                prompt.content = content
                prompt.git_ref = git_ref
            else:
                prompt = Prompt(title=title, content=content, git_ref=git_ref)
                db.session.add(prompt)

            logging.info("Committing changes to database")
            db.session.commit()
            logging.info(f"Prompt saved successfully with ID: {prompt.id}")
        except Exception as e:
            logging.exception(f"Error saving prompt: {e}")
            db.session.rollback()
            raise
        else:
            return prompt

    def get_prompt_with_files(self, prompt_id: int) -> dict:
        """Get a prompt with its associated file contents."""
        try:
            prompt = Prompt.query.get(prompt_id)
            if not prompt:
                self._raise_prompt_not_found(prompt_id)
        except Exception as e:
            logging.exception(f"Error in get_prompt_with_files: {e}")
            raise

        try:
            resolved_content = self.process_prompt(
                prompt.content, FenceFormat.TRIPLE_QUOTES
            )
        except Exception as e:
            logging.exception(f"Error processing prompt content: {e}")
            raise
        else:
            return {
                "id": prompt.id,
                "title": prompt.title,
                "content": resolved_content,
                "raw_content": prompt.content,
                "git_ref": prompt.git_ref,
                "created_at": prompt.created_at,
                "updated_at": prompt.updated_at,
            }
