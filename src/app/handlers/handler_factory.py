"""Reference handler factory module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from src.app.utils.exceptions import ReferenceError

from .api_handler import APIHandler
from .file_handler import FileHandler
from .variable_handler import VariableHandler

if TYPE_CHECKING:
    from .reference_handler import ReferenceHandler


class ReferenceHandlerFactory:
    """Factory for creating reference type handlers."""

    _handlers: ClassVar[dict[str, type[ReferenceHandler]]] = {
        "file": FileHandler,
        "api": APIHandler,
        "variable": VariableHandler,
    }

    @classmethod
    def get_handler(cls, reference: dict[str, Any]) -> ReferenceHandler:
        """Get appropriate handler for reference.

        Args:
            reference: Reference dictionary with 'type' key

        Returns:
            Appropriate reference handler instance

        Raises:
            ReferenceError: If reference type is invalid or missing
        """
        if not isinstance(reference, dict):
            msg = "Reference must be a dictionary"
            raise ReferenceError(msg)

        ref_type = reference.get("type")
        if not ref_type:
            msg = "Missing required field 'type' in reference"
            raise ReferenceError(msg)

        handler_class = cls._handlers.get(ref_type)
        if not handler_class:
            msg = f"Invalid reference type: {ref_type}"
            raise ReferenceError(msg)

        return handler_class()

    @classmethod
    def register_handler(
        cls, reference_type: str, handler_class: type[ReferenceHandler]
    ) -> None:
        """Register a new handler type.

        Args:
            reference_type: Type identifier for the handler
            handler_class: Handler class to register
        """
        cls._handlers[reference_type] = handler_class
