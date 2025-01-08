"""Error notification service for handling and broadcasting application errors."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from weakref import WeakSet

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for error notifications."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorNotification:
    """Represents an error notification with metadata."""

    message: str
    severity: ErrorSeverity
    source: str
    timestamp: datetime
    details: dict | None = None
    error_code: str | None = None

    def to_dict(self) -> dict:
        """Convert notification to dictionary format."""
        return {
            "message": self.message,
            "severity": self.severity.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details or {},
            "error_code": self.error_code,
        }


class ErrorNotificationService:
    """Service for managing and broadcasting error notifications."""

    _instance = None

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the notification service."""
        if not hasattr(self, "_initialized"):
            self._listeners: WeakSet = WeakSet()
            self._recent_notifications: list[ErrorNotification] = []
            self._max_recent = 100
            self._lock = asyncio.Lock()
            self._initialized = True

    def add_listener(self, callback: Callable[[ErrorNotification], None]) -> None:
        """Add a listener for error notifications.

        Args:
            callback: Function to be called with new notifications
        """
        if not callable(callback):
            raise TypeError("Callback must be callable")
        self._listeners.add(callback)

    def remove_listener(self, callback: Callable[[ErrorNotification], None]) -> None:
        """Remove a notification listener."""
        self._listeners.discard(callback)

    async def notify(
        self,
        message: str,
        severity: ErrorSeverity,
        source: str,
        details: dict | None = None,
        error_code: str | None = None,
    ) -> None:
        """Send a new error notification.

        Args:
            message: Human-readable error message
            severity: Error severity level
            source: Component/module that generated the error
            details: Additional error details
            error_code: Optional error code for categorization
        """
        notification = ErrorNotification(
            message=message,
            severity=severity,
            source=source,
            timestamp=datetime.now(),
            details=details,
            error_code=error_code,
        )

        async with self._lock:
            self._recent_notifications.append(notification)
            if len(self._recent_notifications) > self._max_recent:
                self._recent_notifications.pop(0)

            log_func = {
                ErrorSeverity.INFO: logger.info,
                ErrorSeverity.WARNING: logger.warning,
                ErrorSeverity.ERROR: logger.error,
                ErrorSeverity.CRITICAL: logger.critical,
            }.get(severity, logger.error)

            log_func(
                f"{source}: {message}",
                extra={
                    "notification": notification.to_dict(),
                    "error_code": error_code,
                },
            )

            for listener in self._listeners:
                try:
                    listener(notification)
                except Exception as e:
                    logger.exception(
                        "Error in notification listener",
                        extra={"listener": str(listener), "error": str(e)},
                    )

    def get_recent_notifications(
        self, limit: int | None = None, severity: ErrorSeverity | None = None
    ) -> list[ErrorNotification]:
        """Get recent notifications with optional filtering.

        Args:
            limit: Maximum number of notifications to return
            severity: Filter by severity level

        Returns:
            List of recent notifications
        """
        notifications = self._recent_notifications

        if severity:
            notifications = [n for n in notifications if n.severity == severity]

        if limit:
            notifications = notifications[-limit:]

        return notifications
