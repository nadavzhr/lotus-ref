"""
Base error hierarchy for the document editing system.

All document-type-specific errors should inherit from
``DocumentError`` so callers can catch a single base type.
"""
from __future__ import annotations



class DocumentError(Exception):
    """Base class for all document editing errors."""


class DocumentParseError(DocumentError):
    """Raised when a line cannot be parsed."""


class DocumentValidationError(DocumentError):
    """Raised when validation of a line or session fails."""
