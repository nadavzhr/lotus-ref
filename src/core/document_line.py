"""
DocumentLine — the unit of display for any configuration document.

Each line in a file becomes one DocumentLine.  The frontend addresses
lines by their 0-based position; ``line_id`` is an internal stable UUID
used only within the backend (e.g. for conflict detection indexes).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from core.interfaces import HasNetSpecs
from core.line_status import LineStatus
from core.validation_result import ValidationResult


@dataclass(frozen=True, slots=True)
class DocumentLine:
    """
    Immutable representation of one line in a document.

    Attributes:
        line_id:           Internal stable UUID used by the backend for
                           conflict-detection indexes and the ``Document``
                           index.  Never exposed to the frontend.
        raw_text:          Original text that was read from the file (preserved
                           for comments, blanks, and unparseable lines).
        data:              Parsed typed data object. ``None`` for non-data lines.
        validation_result: Single source of truth for the line's health.
                           Holds the status (OK / WARNING / ERROR / COMMENT / EMPTY)
                           and any associated error or warning messages.
    """
    line_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    raw_text: str = ""
    data: HasNetSpecs | None = None
    validation_result: ValidationResult = field(default_factory=ValidationResult)

    @property
    def status(self) -> LineStatus:
        """Convenience accessor — delegates to ``validation_result.status``."""
        return self.validation_result.status
