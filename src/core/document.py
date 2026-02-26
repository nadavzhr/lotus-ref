"""
Document — ordered, ID-indexed container of DocumentLines.

The Document is the **single in-memory representation** of a configuration
file.  It is the source of truth for:

- The frontend viewer   → line content + validation status for coloring
- The edit services      → read a line (by id) into a controller, write it back
- The persistence layer  → serialize all lines back to disk

Lines are addressed by stable UUID (``line_id``), never by index.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from core.document_type import DocumentType
from core.document_line import DocumentLine

if TYPE_CHECKING:
    pass  # reserved for future type-only imports


class Document:
    """
    Mutable ordered collection of :class:`DocumentLine` objects.

    Internal invariant: ``_index[line.line_id] == position`` for every
    line.  The index is rebuilt after any structural mutation (insert /
    remove).  Updates that only change ``data`` or ``status`` inside an
    existing ``DocumentLine`` do *not* need a rebuild.
    """

    __slots__ = ("doc_type", "file_path", "_lines", "_index")

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
        self._rebuild_index()

    # ------------------------------------------------------------------
    # Read access
    # ------------------------------------------------------------------

    @property
    def lines(self) -> tuple[DocumentLine, ...]:
        """Return a tuple copy so callers cannot break internal ordering."""
        return tuple(self._lines)

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

    def insert_line(self, position: int, line: DocumentLine) -> None:
        """Insert a line at the given 0-based position."""
        if line.line_id in self._index:
            raise ValueError(f"Duplicate line_id: {line.line_id}")
        self._lines.insert(position, line)
        self._rebuild_index()

    def remove_line(self, line_id: str) -> DocumentLine:
        """Remove and return a line by its UUID.  Raises KeyError."""
        pos = self._index[line_id]
        removed = self._lines.pop(pos)
        self._rebuild_index()
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
