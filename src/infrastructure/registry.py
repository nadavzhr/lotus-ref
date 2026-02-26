"""
Registry — maps DocumentType to the handler functions for that type.

Adding a new document type requires:
1. Add an enum value to ``DocumentType``
2. Write parser / serializer / validator modules
3. Add one ``register()`` call in ``_registrations.py``

That's it.  Nothing else needs to change — ``document_io`` and the
rest of the system discover handlers through ``get_handler()``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, TYPE_CHECKING

from core.document_type import DocumentType
from core.document_line import LineData

if TYPE_CHECKING:
    from core.validation_result import ValidationResult
    from core.interfaces import INetlistQueryService


@dataclass(frozen=True, slots=True)
class DocumentTypeHandler:
    """Bundle of functions that know how to handle one document type."""
    is_comment: Callable[[str], bool]
    is_empty: Callable[[str], bool]
    parse: Callable[[str], LineData]
    serialize: Callable[[LineData], str]
    validate: Callable[[LineData, Optional["INetlistQueryService"]], "ValidationResult"]


_handlers: dict[DocumentType, DocumentTypeHandler] = {}


def register(doc_type: DocumentType, handler: DocumentTypeHandler) -> None:
    """Register a handler for a document type.  Raises on duplicates."""
    if doc_type in _handlers:
        raise ValueError(f"Handler already registered for {doc_type!r}")
    _handlers[doc_type] = handler


def get_handler(doc_type: DocumentType) -> DocumentTypeHandler:
    """Look up the handler for a document type.  Raises on missing."""
    try:
        return _handlers[doc_type]
    except KeyError:
        raise ValueError(
            f"No handler registered for {doc_type!r}. "
            f"Did you forget to add a register() call in _registrations.py?"
        ) from None
