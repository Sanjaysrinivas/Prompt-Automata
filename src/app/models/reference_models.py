from __future__ import annotations

import hmac
import re
import secrets
from enum import Enum
from pathlib import Path
from typing import ClassVar

import bcrypt
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import db


class ReferenceType(str, Enum):
    """Types of references that can be used in fences."""

    FILE = "file"
    VARIABLE = "variable"
    API = "api"


class PersistentVariable(db.Model):
    """Model for storing persistent variables that can be referenced across fences."""

    __tablename__ = "persistent_variables"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        """String representation of the variable."""
        return f"<PersistentVariable name='{self.name}'>"


class FenceReference(db.Model):
    """Model for tracking references within fences."""

    __tablename__ = "fence_references"

    id = Column(Integer, primary_key=True)
    fence_id = Column(
        Integer, ForeignKey("fence.id", ondelete="CASCADE"), nullable=False
    )
    reference_type = Column(SQLEnum(ReferenceType), nullable=False)
    reference_value = Column(String(500), nullable=False)
    resolved_value = Column(Text)
    last_resolved_at = Column(DateTime)
    error_message = Column(Text)
    reference_metadata = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    fence = relationship("src.app.models.fence.Fence", back_populates="references")

    def __repr__(self) -> str:
        """String representation of the reference."""
        return f"<FenceReference {self.reference_type}:{self.reference_value}>"


class AllowedDirectory(db.Model):
    """Model for storing base directories for file references."""

    __tablename__ = "allowed_directory"

    id = Column(Integer, primary_key=True)
    path = Column(String(500), nullable=False, unique=True)
    description = Column(Text)
    is_recursive = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @classmethod
    def ensure_default_directory(cls):
        """Ensure the default allowed directory exists."""
        default_path = Path.cwd()
        if not cls.query.filter_by(path=str(default_path)).first():
            default_dir = cls(
                path=str(default_path),
                description="Default workspace directory",
                is_recursive=True,
            )
            db.session.add(default_dir)
            db.session.commit()

    def get_relative_path(self, target_path: str) -> str | None:
        """Get relative path from this base directory."""
        try:
            return str(Path(target_path).relative_to(Path(self.path)))
        except ValueError:
            return None

    @classmethod
    async def is_path_allowed(cls, target_path: str) -> tuple[bool, str | None]:
        """Check if a path is allowed based on configured directories.

        Args:
            target_path: The path to check

        Returns:
            Tuple of (is_allowed, error_message)
        """
        try:
            cls.ensure_default_directory()
            target = Path(target_path).resolve()
            if not target.exists():
                return False, f"Path does not exist: {target_path}"
            allowed_dirs = cls.query.all()
            if not allowed_dirs:
                return False, "No allowed directories configured"
            for allowed_dir in allowed_dirs:
                base_path = Path(allowed_dir.path).resolve()
                try:
                    relative = target.relative_to(base_path)
                except ValueError:
                    continue
                else:
                    if allowed_dir.is_recursive or len(relative.parts) <= 1:
                        return True, None
        except (ValueError, FileNotFoundError, OSError) as e:
            return False, f"Error checking path: {e!s}"
        else:
            return False, f"Path is not within allowed directories: {target_path}"

    def __repr__(self) -> str:
        """String representation of the directory."""
        return f"<AllowedDirectory path='{self.path}'>"


class APIKeyError(Exception):
    """Base exception for API key errors."""


class InvalidKeyFormatError(APIKeyError):
    """Raised when the API key format is invalid."""


class WeakKeyError(APIKeyError):
    """Raised when the API key doesn't meet security requirements."""


class APIKey(db.Model):
    """Model for storing API keys."""

    __tablename__ = "api_keys"

    MIN_LENGTH: ClassVar[int] = 32
    MAX_LENGTH: ClassVar[int] = 128
    KEY_PATTERN: ClassVar[re.Pattern] = re.compile(r"^[A-Za-z0-9\-._~]+$")
    REQUIRED_CHAR_CLASSES: ClassVar[list[tuple[str, str]]] = [
        (r"[A-Z]", "uppercase letter"),
        (r"[a-z]", "lowercase letter"),
        (r"[0-9]", "number"),
        (r"[-._~]", "special character"),
    ]
    MIN_UNIQUE_CHARS: ClassVar[int] = 8
    PEPPER_LENGTH: ClassVar[int] = 32

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    key = Column(String(500), nullable=False)
    key_version = Column(Integer, default=1)
    pepper = Column(String(64), nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __init__(self, name: str, key: str):
        """Initialize the API key with hashing.

        Args:
            name: Name of the API key
            key: The API key to hash and store

        Raises:
            InvalidKeyFormatError: If the key format is invalid
            WeakKeyError: If the key doesn't meet security requirements
        """
        self.name = name
        self.set_key(key)

    def set_key(self, key: str):
        """Hash and set the API key with comprehensive validation.

        Args:
            key: The API key to hash and store

        Raises:
            InvalidKeyFormatError: If the key format is invalid
            WeakKeyError: If the key doesn't meet security requirements
        """
        if not isinstance(key, str):
            msg = "API key must be a string"
            raise InvalidKeyFormatError(msg)
        if len(key) < self.MIN_LENGTH:
            msg = f"API key must be at least {self.MIN_LENGTH} characters long"
            raise InvalidKeyFormatError(msg)
        if len(key) > self.MAX_LENGTH:
            msg = f"API key cannot be longer than {self.MAX_LENGTH} characters"
            raise InvalidKeyFormatError(msg)
        if not self.KEY_PATTERN.match(key):
            msg = "API key contains invalid characters. Only alphanumeric characters and -._~ are allowed"
            raise InvalidKeyFormatError(msg)
        for pattern, char_type in self.REQUIRED_CHAR_CLASSES:
            if not re.search(pattern, key):
                msg = f"API key must contain at least one {char_type}"
                raise WeakKeyError(msg)
        if len(set(key)) < self.MIN_UNIQUE_CHARS:
            msg = f"API key must contain at least {self.MIN_UNIQUE_CHARS} unique characters"
            raise WeakKeyError(msg)
        if self._contains_common_patterns(key):
            msg = "API key contains common patterns or sequences"
            raise WeakKeyError(msg)

        pepper = secrets.token_bytes(self.PEPPER_LENGTH)
        self.pepper = pepper.hex()

        peppered_key = hmac.new(pepper, key.encode(), "sha256").digest()
        salt = bcrypt.gensalt()
        hashed_key = bcrypt.hashpw(peppered_key, salt)

        if not hmac.compare_digest(bcrypt.hashpw(peppered_key, hashed_key), hashed_key):
            msg = "Key hashing verification failed"
            raise ValueError(msg)

        self.key = hashed_key.decode()
        self.key_version += 1

    def verify_key(self, key: str) -> bool:
        """Verify if the provided key matches the stored hash.

        Args:
            key: The key to verify

        Returns:
            bool: True if the key matches, False otherwise
        """
        try:
            pepper = bytes.fromhex(self.pepper)
            peppered_key = hmac.new(pepper, key.encode(), "sha256").digest()
            return hmac.compare_digest(
                bcrypt.hashpw(peppered_key, self.key.encode()), self.key.encode()
            )
        except (ValueError, AttributeError):
            return False

    def revoke(self):
        """Revoke this API key."""
        self.revoked_at = func.now()

    def is_revoked(self) -> bool:
        """Check if this API key has been revoked.

        Returns:
            bool: True if the key is revoked, False otherwise
        """
        return self.revoked_at is not None

    def update_last_used(self):
        """Update the last used timestamp."""
        self.last_used_at = func.now()

    def _contains_common_patterns(self, key: str) -> bool:
        """Check if the key contains common patterns that would make it weak.

        Args:
            key: The key to check

        Returns:
            bool: True if common patterns are found, False otherwise
        """
        for i in range(len(key) - 3):
            if len(set(key[i : i + 4])) == 1:
                return True

        sequences = [
            "abcdefghijklmnopqrstuvwxyz",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "0123456789",
        ]

        for seq in sequences:
            for i in range(len(seq) - 3):
                if seq[i : i + 4].lower() in key.lower():
                    return True

        keyboard_patterns = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]

        for pattern in keyboard_patterns:
            for i in range(len(pattern) - 3):
                if pattern[i : i + 4].lower() in key.lower():
                    return True

        return False

    def __repr__(self) -> str:
        """String representation of the API key."""
        status = "revoked" if self.is_revoked() else "active"
        return f"<APIKey name='{self.name}' status='{status}'>"
