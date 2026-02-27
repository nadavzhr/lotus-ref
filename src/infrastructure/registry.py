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
from typing import Any, Callable, Generic, Optional, TypeVar, TYPE_CHECKING

from core.document_type import DocumentType

if TYPE_CHECKING:
    from core.validation_result import ValidationResult
    from core.interfaces import INetlistQueryService

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class DocumentTypeHandler(Generic[T]):
    """Bundle of functions that know how to handle one document type.

    Generic over the line-data type ``T`` (e.g. ``AfLineData``,
    ``MutexLineData``).  The registry erases this parameter so
    callers after ``get_handler()`` operate on ``Any``.
    """
    is_comment: Callable[[str], bool]
    is_empty: Callable[[str], bool]
    parse: Callable[[str], T]
    serialize: Callable[[T], str]
    validate: Callable[[T, Optional["INetlistQueryService"]], "ValidationResult"]


_handlers: dict[DocumentType, DocumentTypeHandler[Any]] = {}


def register(doc_type: DocumentType, handler: DocumentTypeHandler[Any]) -> None:
    """Register a handler for a document type.  Raises on duplicates."""
    if doc_type in _handlers:
        raise ValueError(f"Handler already registered for {doc_type!r}")
    _handlers[doc_type] = handler


def get_handler(doc_type: DocumentType) -> DocumentTypeHandler[Any]:
    """Look up the handler for a document type.  Raises on missing."""
    try:
        return _handlers[doc_type]
    except KeyError:
        raise ValueError(
            f"No handler registered for {doc_type!r}. "
            f"Did you forget to add a register() call in _registrations.py?"
        ) from None
