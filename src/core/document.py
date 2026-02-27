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
from dataclasses import dataclass
from typing import Optional, Protocol

from core.document_type import DocumentType
from core.document_line import DocumentLine

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Mutation record — returned by undo() / redo() so callers can
# synchronize external state (e.g. conflict detection) without
# coupling to the undo internals.
# ------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MutationRecord:
    """Describes a mutation that was applied to a :class:`Document`.

    Attributes:
        kind:     ``"insert"`` | ``"remove"`` | ``"replace"`` | ``"swap"``
        position: 0-based line position at the time of the mutation.
                  For swaps this is the *lower* of the two positions.
        line_id:  Stable UUID of the affected line (for swaps, the line
                  that was at *position* before the swap).
        old_line: The line that was removed or replaced (``None`` for
                  insert and swap).
        new_line: The line that was inserted or is the replacement
                  (``None`` for remove and swap).
        position2: Second position involved in a swap (``None`` otherwise).
    """
    kind: str
    position: int
    line_id: str
    old_line: Optional[DocumentLine] = None
    new_line: Optional[DocumentLine] = None
    position2: Optional[int] = None


# ------------------------------------------------------------------
# Internal command objects (private to this module)
# ------------------------------------------------------------------

class _Command(Protocol):
    """Reversible mutation — every command knows how to undo and redo itself."""
    def undo(self, doc: Document) -> MutationRecord: ...
    def redo(self, doc: Document) -> MutationRecord: ...


class _InsertCmd:
    """Reversible insert — undo removes the line, redo re-inserts it."""
    __slots__ = ("_position", "_line")

    def __init__(self, position: int, line: DocumentLine) -> None:
        self._position = position
        self._line = line

    def undo(self, doc: Document) -> MutationRecord:
        pos = doc.get_position(self._line.line_id)
        doc._raw_remove_line(self._line.line_id)
        return MutationRecord("remove", pos, self._line.line_id,
                              old_line=self._line)

    def redo(self, doc: Document) -> MutationRecord:
        doc._raw_insert_line(self._position, self._line)
        return MutationRecord("insert", self._position, self._line.line_id,
                              new_line=self._line)


class _RemoveCmd:
    """Reversible remove — undo re-inserts the line, redo removes it."""
    __slots__ = ("_position", "_line")

    def __init__(self, position: int, line: DocumentLine) -> None:
        self._position = position
        self._line = line

    def undo(self, doc: Document) -> MutationRecord:
        doc._raw_insert_line(self._position, self._line)
        return MutationRecord("insert", self._position, self._line.line_id,
                              new_line=self._line)

    def redo(self, doc: Document) -> MutationRecord:
        doc._raw_remove_line(self._line.line_id)
        return MutationRecord("remove", self._position, self._line.line_id,
                              old_line=self._line)


class _ReplaceCmd:
    """Reversible replace — undo restores the old line, redo reapplies."""
    __slots__ = ("_old_line", "_new_line")

    def __init__(self, old_line: DocumentLine, new_line: DocumentLine) -> None:
        self._old_line = old_line
        self._new_line = new_line

    def undo(self, doc: Document) -> MutationRecord:
        pos = doc.get_position(self._new_line.line_id)
        doc._raw_replace_line(self._new_line.line_id, self._old_line)
        return MutationRecord("replace", pos, self._old_line.line_id,
                              old_line=self._new_line, new_line=self._old_line)

    def redo(self, doc: Document) -> MutationRecord:
        pos = doc.get_position(self._old_line.line_id)
        doc._raw_replace_line(self._old_line.line_id, self._new_line)
        return MutationRecord("replace", pos, self._new_line.line_id,
                              old_line=self._old_line, new_line=self._new_line)


class _SwapCmd:
    """Reversible swap of two adjacent lines."""
    __slots__ = ("_pos_a", "_pos_b")

    def __init__(self, pos_a: int, pos_b: int) -> None:
        self._pos_a = pos_a
        self._pos_b = pos_b

    def undo(self, doc: Document) -> MutationRecord:
        # Swapping again reverses the original swap
        line_a = doc._lines[self._pos_a]
        doc._raw_swap_lines(self._pos_a, self._pos_b)
        return MutationRecord("swap", min(self._pos_a, self._pos_b),
                              line_a.line_id,
                              position2=max(self._pos_a, self._pos_b))

    def redo(self, doc: Document) -> MutationRecord:
        line_a = doc._lines[self._pos_a]
        doc._raw_swap_lines(self._pos_a, self._pos_b)
        return MutationRecord("swap", min(self._pos_a, self._pos_b),
                              line_a.line_id,
                              position2=max(self._pos_a, self._pos_b))


class Document:
    """
    Mutable ordered collection of :class:`DocumentLine` objects.

    Internal invariant: ``_index[line.line_id] == position`` for every
    line.  The index is maintained incrementally on insert / remove /
    replace.  Updates that only change ``data`` or ``status`` inside an
    existing ``DocumentLine`` do *not* need an index update.
    """

    __slots__ = ("doc_type", "file_path", "_lines", "_index", "_lines_cache",
                 "_undo_stack", "_redo_stack")

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
        self._undo_stack: list[_Command] = []
        self._redo_stack: list[_Command] = []
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
    # Bulk operations (no undo recording)
    # ------------------------------------------------------------------

    def append_line(self, line: DocumentLine) -> None:
        """Add a line to the end.  Construction-time only — not recorded."""
        if line.line_id in self._index:
            raise ValueError(f"Duplicate line_id: {line.line_id}")
        self._lines.append(line)
        self._index[line.line_id] = len(self._lines) - 1
        self._lines_cache = None

    # ------------------------------------------------------------------
    # Mutations (recorded to undo stack)
    # ------------------------------------------------------------------

    def insert_line(self, position: int, line: DocumentLine) -> None:
        """Insert *line* at *position*.  Recorded for undo."""
        self._raw_insert_line(position, line)
        self._undo_stack.append(_InsertCmd(position, line))
        self._redo_stack.clear()

    def remove_line(self, line_id: str) -> DocumentLine:
        """Remove and return a line by UUID.  Recorded for undo."""
        pos = self.get_position(line_id)
        removed = self._raw_remove_line(line_id)
        self._undo_stack.append(_RemoveCmd(pos, removed))
        self._redo_stack.clear()
        return removed

    def replace_line(self, line_id: str, new_line: DocumentLine) -> None:
        """Replace a line in-place.  Recorded for undo."""
        old_line = self.get_line(line_id)
        self._raw_replace_line(line_id, new_line)
        self._undo_stack.append(_ReplaceCmd(old_line, new_line))
        self._redo_stack.clear()

    def swap_lines(self, pos_a: int, pos_b: int) -> None:
        """Swap two lines by position.  Recorded for undo.

        Raises ``IndexError`` if either position is out of range, and
        ``ValueError`` if the positions are identical.
        """
        if pos_a == pos_b:
            raise ValueError("Cannot swap a line with itself")
        self._raw_swap_lines(pos_a, pos_b)
        self._undo_stack.append(_SwapCmd(pos_a, pos_b))
        self._redo_stack.clear()

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    @property
    def can_undo(self) -> bool:
        """``True`` if there is at least one operation to undo."""
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        """``True`` if there is at least one operation to redo."""
        return bool(self._redo_stack)

    def undo(self) -> MutationRecord | None:
        """Undo the most recent mutation.

        Returns a :class:`MutationRecord` describing the *applied*
        reversal (e.g. undoing an insert returns a ``"remove"`` record),
        or ``None`` if the undo stack is empty.
        """
        if not self._undo_stack:
            return None
        cmd = self._undo_stack.pop()
        record = cmd.undo(self)
        self._redo_stack.append(cmd)
        logger.debug("Undo: %s line %s at position %d",
                     record.kind, record.line_id, record.position)
        return record

    def redo(self) -> MutationRecord | None:
        """Redo the most recently undone mutation.

        Returns a :class:`MutationRecord` describing the *applied*
        mutation, or ``None`` if the redo stack is empty.
        """
        if not self._redo_stack:
            return None
        cmd = self._redo_stack.pop()
        record = cmd.redo(self)
        self._undo_stack.append(cmd)
        logger.debug("Redo: %s line %s at position %d",
                     record.kind, record.line_id, record.position)
        return record

    # ------------------------------------------------------------------
    # Raw mutations (no recording — used by command undo/redo)
    # ------------------------------------------------------------------

    def _raw_insert_line(self, position: int, line: DocumentLine) -> None:
        if line.line_id in self._index:
            raise ValueError(f"Duplicate line_id: {line.line_id}")
        self._lines.insert(position, line)
        self._lines_cache = None
        for lid, idx in self._index.items():
            if idx >= position:
                self._index[lid] = idx + 1
        self._index[line.line_id] = position

    def _raw_remove_line(self, line_id: str) -> DocumentLine:
        pos = self._index.pop(line_id)
        removed = self._lines.pop(pos)
        self._lines_cache = None
        for lid, idx in self._index.items():
            if idx > pos:
                self._index[lid] = idx - 1
        return removed

    def _raw_replace_line(self, line_id: str, new_line: DocumentLine) -> None:
        pos = self._index.pop(line_id)
        self._lines[pos] = new_line
        self._lines_cache = None
        logger.debug("Replaced line %s at position %d", line_id, pos)
        if new_line.line_id != line_id:
            self._index[new_line.line_id] = pos
        else:
            self._index[line_id] = pos

    def _raw_swap_lines(self, pos_a: int, pos_b: int) -> None:
        """Swap two lines by position without recording to undo."""
        # Bounds check
        if not (0 <= pos_a < len(self._lines)):
            raise IndexError(f"Position {pos_a} out of range")
        if not (0 <= pos_b < len(self._lines)):
            raise IndexError(f"Position {pos_b} out of range")

        line_a = self._lines[pos_a]
        line_b = self._lines[pos_b]
        self._lines[pos_a] = line_b
        self._lines[pos_b] = line_a
        self._index[line_a.line_id] = pos_b
        self._index[line_b.line_id] = pos_a
        self._lines_cache = None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _rebuild_index(self) -> None:
        self._index = {line.line_id: i for i, line in enumerate(self._lines)}
