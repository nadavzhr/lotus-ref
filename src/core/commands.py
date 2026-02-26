"""
Command pattern for document operations — enables undo / redo.

Every mutation on a :class:`Document` can be wrapped in a concrete
:class:`ICommand` and pushed onto an :class:`UndoRedoStack`.

Concrete commands
-----------------
- :class:`AppendLineCommand`
- :class:`InsertLineCommand`
- :class:`RemoveLineCommand`
- :class:`ReplaceLineCommand`
- :class:`SwapLinesCommand`
- :class:`ToggleLineCommentCommand`
"""
from __future__ import annotations

import abc
from typing import Callable, Sequence, TYPE_CHECKING

from core.document_line import DocumentLine
from core.line_status import LineStatus
from core.validation_result import ValidationResult

if TYPE_CHECKING:
    from core.document import Document


# ------------------------------------------------------------------
# Abstract base
# ------------------------------------------------------------------

class ICommand(abc.ABC):
    """A reversible document operation."""

    @abc.abstractmethod
    def execute(self) -> None:
        """Apply the operation to the document."""

    @abc.abstractmethod
    def undo(self) -> None:
        """Reverse the operation, restoring previous state."""


# ------------------------------------------------------------------
# Undo / Redo stack
# ------------------------------------------------------------------

class UndoRedoStack:
    """
    Manages a linear history of executed commands.

    * :meth:`execute` — run a command and push it onto the undo stack.
    * :meth:`undo` — pop the most recent command and reverse it.
    * :meth:`redo` — re-apply the most recently undone command.

    Any new :meth:`execute` after an undo discards the redo history
    (standard linear undo model).
    """

    __slots__ = ("_undo_stack", "_redo_stack")

    def __init__(self) -> None:
        self._undo_stack: list[ICommand] = []
        self._redo_stack: list[ICommand] = []

    # -- public API ------------------------------------------------

    def execute(self, command: ICommand) -> None:
        """Execute *command* and push it onto the undo stack."""
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()

    def undo(self) -> None:
        """Undo the most recent command.  Raises *IndexError* if empty."""
        if not self._undo_stack:
            raise IndexError("Nothing to undo")
        cmd = self._undo_stack.pop()
        cmd.undo()
        self._redo_stack.append(cmd)

    def redo(self) -> None:
        """Redo the most recently undone command.  Raises *IndexError* if empty."""
        if not self._redo_stack:
            raise IndexError("Nothing to redo")
        cmd = self._redo_stack.pop()
        cmd.execute()
        self._undo_stack.append(cmd)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def clear(self) -> None:
        """Discard all history."""
        self._undo_stack.clear()
        self._redo_stack.clear()


# ------------------------------------------------------------------
# Concrete commands for existing Document mutations
# ------------------------------------------------------------------

class AppendLineCommand(ICommand):
    """Wraps :meth:`Document.append_line`."""

    __slots__ = ("_document", "_line")

    def __init__(self, document: Document, line: DocumentLine) -> None:
        self._document = document
        self._line = line

    def execute(self) -> None:
        self._document.append_line(self._line)

    def undo(self) -> None:
        self._document.remove_line(self._line.line_id)


class InsertLineCommand(ICommand):
    """Wraps :meth:`Document.insert_line`."""

    __slots__ = ("_document", "_position", "_line")

    def __init__(self, document: Document, position: int, line: DocumentLine) -> None:
        self._document = document
        self._position = position
        self._line = line

    def execute(self) -> None:
        self._document.insert_line(self._position, self._line)

    def undo(self) -> None:
        self._document.remove_line(self._line.line_id)


class RemoveLineCommand(ICommand):
    """Wraps :meth:`Document.remove_line`."""

    __slots__ = ("_document", "_line_id", "_removed_line", "_position")

    def __init__(self, document: Document, line_id: str) -> None:
        self._document = document
        self._line_id = line_id
        self._removed_line: DocumentLine | None = None
        self._position: int | None = None

    def execute(self) -> None:
        self._position = self._document.get_position(self._line_id)
        self._removed_line = self._document.remove_line(self._line_id)

    def undo(self) -> None:
        assert self._removed_line is not None and self._position is not None
        self._document.insert_line(self._position, self._removed_line)


class ReplaceLineCommand(ICommand):
    """Wraps :meth:`Document.replace_line`."""

    __slots__ = ("_document", "_line_id", "_new_line", "_old_line")

    def __init__(self, document: Document, line_id: str, new_line: DocumentLine) -> None:
        self._document = document
        self._line_id = line_id
        self._new_line = new_line
        self._old_line: DocumentLine | None = None

    def execute(self) -> None:
        self._old_line = self._document.get_line(self._line_id)
        self._document.replace_line(self._line_id, self._new_line)

    def undo(self) -> None:
        assert self._old_line is not None
        self._document.replace_line(self._new_line.line_id, self._old_line)


# ------------------------------------------------------------------
# New commands
# ------------------------------------------------------------------

class SwapLinesCommand(ICommand):
    """
    Swap the current line with the adjacent line above or below.

    *direction* must be ``"up"`` (swap with predecessor) or ``"down"``
    (swap with successor).  Raises ``IndexError`` when the line is
    already at the corresponding boundary.
    """

    __slots__ = ("_document", "_line_id", "_direction", "_other_id")

    def __init__(self, document: Document, line_id: str, direction: str) -> None:
        if direction not in ("up", "down"):
            raise ValueError(f"direction must be 'up' or 'down', got {direction!r}")
        self._document = document
        self._line_id = line_id
        self._direction = direction
        self._other_id: str | None = None

    def execute(self) -> None:
        pos = self._document.get_position(self._line_id)
        target = pos - 1 if self._direction == "up" else pos + 1

        if target < 0 or target >= len(self._document):
            raise IndexError(
                f"Cannot swap {self._direction}: line is already at the boundary"
            )

        self._other_id = self._document[target].line_id
        self._document.swap_lines(self._line_id, self._other_id)

    def undo(self) -> None:
        assert self._other_id is not None
        self._document.swap_lines(self._line_id, self._other_id)


class ToggleLineCommentCommand(ICommand):
    """
    Comment or uncomment the selected line(s).

    * **Commenting** — prepends ``"# "`` and sets status to COMMENT.
      The ``line_id`` is preserved so the frontend can track the line.
    * **Uncommenting** — strips the ``#`` prefix and **fully
      re-processes** the text via the caller-supplied *parse_fn*.
      A new ``line_id`` is assigned so no stale status is reused.

    Parameters
    ----------
    document : Document
        The target document.
    line_ids : sequence of str
        IDs of lines to toggle.
    parse_fn : callable
        ``(raw_text: str) -> DocumentLine`` — used when uncommenting
        to re-parse the raw text into a brand-new ``DocumentLine``
        (fresh UUID, fresh validation).
    """

    COMMENT_PREFIX = "# "

    __slots__ = ("_document", "_line_ids", "_parse_fn", "_snapshots", "_executed")

    def __init__(
        self,
        document: Document,
        line_ids: Sequence[str],
        parse_fn: Callable[[str], DocumentLine],
    ) -> None:
        self._document = document
        self._line_ids = list(line_ids)
        self._parse_fn = parse_fn
        # (old_line, new_line) pairs — computed once on first execute
        self._snapshots: list[tuple[DocumentLine, DocumentLine]] = []
        self._executed = False

    def execute(self) -> None:
        if not self._executed:
            self._first_execute()
            self._executed = True
        else:
            self._replay_execute()

    def undo(self) -> None:
        for old_line, new_line in reversed(self._snapshots):
            self._document.replace_line(new_line.line_id, old_line)

    # -- internal --------------------------------------------------

    def _first_execute(self) -> None:
        """Compute new lines and apply them (first run)."""
        self._snapshots = []
        for line_id in self._line_ids:
            old_line = self._document.get_line(line_id)

            if old_line.status == LineStatus.COMMENT:
                new_line = self._uncomment(old_line)
            else:
                new_line = self._comment(old_line)

            self._snapshots.append((old_line, new_line))
            self._document.replace_line(old_line.line_id, new_line)

    def _replay_execute(self) -> None:
        """Re-apply saved snapshots (redo path)."""
        for old_line, new_line in self._snapshots:
            self._document.replace_line(old_line.line_id, new_line)

    def _comment(self, line: DocumentLine) -> DocumentLine:
        """Prefix with ``# `` and mark as COMMENT, keeping the same ID."""
        return DocumentLine(
            line_id=line.line_id,
            raw_text=self.COMMENT_PREFIX + line.raw_text,
            validation_result=ValidationResult(status=LineStatus.COMMENT),
        )

    def _uncomment(self, line: DocumentLine) -> DocumentLine:
        """Strip comment prefix and fully re-parse (fresh identity)."""
        raw = line.raw_text.lstrip()
        if raw.startswith("# "):
            raw = raw[2:]
        elif raw.startswith("#"):
            raw = raw[1:]
        return self._parse_fn(raw)
