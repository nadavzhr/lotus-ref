"""Internal undo/redo command objects for :mod:`core.document`."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from core.document_line import DocumentLine


@dataclass(frozen=True, slots=True)
class MutationRecord:
    """Describes a mutation that was applied to a document."""

    kind: str
    position: int
    line_id: str
    old_line: Optional[DocumentLine] = None
    new_line: Optional[DocumentLine] = None
    position2: Optional[int] = None


class DocumentCommandTarget(Protocol):
    """Minimal surface commands need from :class:`core.document.Document`."""

    _lines: list[DocumentLine]

    def get_position(self, line_id: str) -> int: ...

    def _apply_insert_line(self, position: int, line: DocumentLine) -> None: ...

    def _apply_remove_line(self, line_id: str) -> DocumentLine: ...

    def _apply_replace_line(self, line_id: str, new_line: DocumentLine) -> None: ...

    def _apply_swap_lines(self, pos_a: int, pos_b: int) -> None: ...


class Command(Protocol):
    """Reversible mutation — every command knows how to undo and redo itself."""

    def undo(self, doc: DocumentCommandTarget) -> MutationRecord: ...

    def redo(self, doc: DocumentCommandTarget) -> MutationRecord: ...


class InsertCmd:
    """Reversible insert — undo removes the line, redo re-inserts it."""

    __slots__ = ("_position", "_line")

    def __init__(self, position: int, line: DocumentLine) -> None:
        self._position = position
        self._line = line

    def undo(self, doc: DocumentCommandTarget) -> MutationRecord:
        pos = doc.get_position(self._line.line_id)
        doc._apply_remove_line(self._line.line_id)
        return MutationRecord("remove", pos, self._line.line_id, old_line=self._line)

    def redo(self, doc: DocumentCommandTarget) -> MutationRecord:
        doc._apply_insert_line(self._position, self._line)
        return MutationRecord("insert", self._position, self._line.line_id, new_line=self._line)


class RemoveCmd:
    """Reversible remove — undo re-inserts the line, redo removes it."""

    __slots__ = ("_position", "_line")

    def __init__(self, position: int, line: DocumentLine) -> None:
        self._position = position
        self._line = line

    def undo(self, doc: DocumentCommandTarget) -> MutationRecord:
        doc._apply_insert_line(self._position, self._line)
        return MutationRecord("insert", self._position, self._line.line_id, new_line=self._line)

    def redo(self, doc: DocumentCommandTarget) -> MutationRecord:
        doc._apply_remove_line(self._line.line_id)
        return MutationRecord("remove", self._position, self._line.line_id, old_line=self._line)


class ReplaceCmd:
    """Reversible replace — undo restores the old line, redo reapplies."""

    __slots__ = ("_old_line", "_new_line")

    def __init__(self, old_line: DocumentLine, new_line: DocumentLine) -> None:
        self._old_line = old_line
        self._new_line = new_line

    def undo(self, doc: DocumentCommandTarget) -> MutationRecord:
        pos = doc.get_position(self._new_line.line_id)
        doc._apply_replace_line(self._new_line.line_id, self._old_line)
        return MutationRecord(
            "replace", pos, self._old_line.line_id, old_line=self._new_line, new_line=self._old_line
        )

    def redo(self, doc: DocumentCommandTarget) -> MutationRecord:
        pos = doc.get_position(self._old_line.line_id)
        doc._apply_replace_line(self._old_line.line_id, self._new_line)
        return MutationRecord(
            "replace", pos, self._new_line.line_id, old_line=self._old_line, new_line=self._new_line
        )


class SwapCmd:
    """Reversible swap of two lines by position."""

    __slots__ = ("_pos_a", "_pos_b")

    def __init__(self, pos_a: int, pos_b: int) -> None:
        self._pos_a = pos_a
        self._pos_b = pos_b

    def undo(self, doc: DocumentCommandTarget) -> MutationRecord:
        line_a = doc._lines[self._pos_a]
        doc._apply_swap_lines(self._pos_a, self._pos_b)
        return MutationRecord(
            "swap",
            min(self._pos_a, self._pos_b),
            line_a.line_id,
            position2=max(self._pos_a, self._pos_b),
        )

    def redo(self, doc: DocumentCommandTarget) -> MutationRecord:
        line_a = doc._lines[self._pos_a]
        doc._apply_swap_lines(self._pos_a, self._pos_b)
        return MutationRecord(
            "swap",
            min(self._pos_a, self._pos_b),
            line_a.line_id,
            position2=max(self._pos_a, self._pos_b),
        )
