"""
Document — ordered, ID-indexed container of DocumentLines.

The Document is the **single in-memory representation** of a configuration
file.  It is the source of truth for:

- The frontend viewer   → line content + validation status for coloring
- The edit services      → read a line (by id) into a controller, write it back
- The persistence layer  → serialize all lines back to disk

Lines are addressed by stable UUID (``line_id``) internally for O(1)
lookups and conflict tracking.  The API layer resolves 0-based positions
to ``line_id`` at the service boundary, so callers outside the backend
never see UUIDs.
"""
from __future__ import annotations

import logging
from typing import Optional

from core.document_type import DocumentType
from core.document_line import DocumentLine

logger = logging.getLogger(__name__)


class Document:
    """
    Mutable ordered collection of :class:`DocumentLine` objects.

    Internal invariant: ``_index[line.line_id] == position`` for every
    line.  The index is maintained incrementally on insert / remove /
    replace.  Updates that only change ``data`` or ``status`` inside an
    existing ``DocumentLine`` do *not* need an index update.
    """

    __slots__ = ("doc_type", "file_path", "_lines", "_index", "_lines_cache")

    def __init__(
        self,
        doc_type: DocumentType,
        file_path: str = "",
        lines: Optional[list[DocumentLine]] = None,
    ):
        self.doc_type: DocumentType = doc_type
        self.file_path: str = file_path
        self._lines: list[DocumentLine] = list(lines) if lines else []
        self._index: dict[str, int] = {}
        self._lines_cache: tuple[DocumentLine, ...] | None = None
        self._rebuild_index()

    # ------------------------------------------------------------------
    # Read access
    # ------------------------------------------------------------------

    @property
    def lines(self) -> tuple[DocumentLine, ...]:
        """Return a cached tuple so callers cannot break internal ordering."""
        if self._lines_cache is None:
            self._lines_cache = tuple(self._lines)
        return self._lines_cache

    def __len__(self) -> int:
        return len(self._lines)

    def __getitem__(self, position: int) -> DocumentLine:
        return self._lines[position]

    def get_line(self, line_id: str) -> DocumentLine:
        """Fetch a line by its stable UUID.  Raises KeyError if not found."""
        pos = self._index[line_id]
        return self._lines[pos]

    def get_position(self, line_id: str) -> int:
        """Return the 0-based position of a line.  Raises KeyError."""
        return self._index[line_id]

    def has_line(self, line_id: str) -> bool:
        return line_id in self._index

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def append_line(self, line: DocumentLine) -> None:
        """Add a line to the end of the document."""
        if line.line_id in self._index:
            raise ValueError(f"Duplicate line_id: {line.line_id}")
        self._lines.append(line)
        self._index[line.line_id] = len(self._lines) - 1
        self._lines_cache = None

    def insert_line(self, position: int, line: DocumentLine) -> None:
        """Insert a line at the given 0-based position."""
        if line.line_id in self._index:
            raise ValueError(f"Duplicate line_id: {line.line_id}")
        self._lines.insert(position, line)
        self._lines_cache = None
        # Shift entries at or after the insertion point up by 1
        for lid, idx in self._index.items():
            if idx >= position:
                self._index[lid] = idx + 1
        self._index[line.line_id] = position

    def remove_line(self, line_id: str) -> DocumentLine:
        """Remove and return a line by its UUID.  Raises KeyError."""
        pos = self._index.pop(line_id)
        removed = self._lines.pop(pos)
        self._lines_cache = None
        # Shift entries after the removed position down by 1
        for lid, idx in self._index.items():
            if idx > pos:
                self._index[lid] = idx - 1
        return removed

    def replace_line(self, line_id: str, new_line: DocumentLine) -> None:
        """
        Replace a line in-place, keeping the same position.

        The new_line's ``line_id`` may differ from the old one
        (e.g. after re-parsing an edited line).  Typically the caller
        will reuse the same ``line_id``.
        """
        pos = self._index.pop(line_id)
        self._lines[pos] = new_line
        self._lines_cache = None
        logger.debug("Replaced line %s at position %d", line_id, pos)
        # If the id changed we need a full rebuild; if same, just update index
        if new_line.line_id != line_id:
            self._rebuild_index()
        else:
            self._index[new_line.line_id] = pos

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _rebuild_index(self) -> None:
        self._index = {line.line_id: i for i, line in enumerate(self._lines)}
