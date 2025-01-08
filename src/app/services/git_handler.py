from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from git import InvalidGitRepositoryError, Repo

if TYPE_CHECKING:
    from git.repo.base import Repo as GitRepo


class GitHandler:
    """Handler for Git-related operations."""

    def __init__(self) -> None:
        """Initialize the Git handler."""
        try:
            self.repo: GitRepo | None = Repo(
                Path(__file__).parent.parent.parent,
                search_parent_directories=True,
            )
        except InvalidGitRepositoryError:
            self.repo = None

    def get_current_commit(self) -> str | None:
        """Get the current Git commit hash.

        Returns:
            str | None: The current commit hash, or None if not in a Git repository.
        """
        if not self.repo:
            return None

        try:
            return self.repo.head.commit.hexsha
        except (ValueError, AttributeError):  # Narrow down exceptions
            return None

    def get_file_history(self, file_path: str) -> list[dict]:
        """Get the Git history for a specific file.

        Args:
            file_path: Path to the file relative to the repository root.

        Returns:
            list[dict]: List of commits that modified the file.
        """
        if not self.repo:
            return []

        try:
            commits = [
                {
                    "hash": commit.hexsha,
                    "author": f"{commit.author.name} <{commit.author.email}>",
                    "date": commit.committed_datetime.isoformat(),
                    "message": commit.message.strip(),
                }
                for commit in self.repo.iter_commits(paths=file_path)
            ]
        except (ValueError, AttributeError):  # Narrow down exceptions
            return []
        else:
            return commits
