import pytest

from core import (
    Document,
    DocumentLine,
    DocumentType,
    LineStatus,
    ValidationResult,
    ICommand,
    UndoRedoStack,
    AppendLineCommand,
    InsertLineCommand,
    RemoveLineCommand,
    ReplaceLineCommand,
    SwapLinesCommand,
    ToggleLineCommentCommand,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _line(line_id: str = "", raw_text: str = "", **kw) -> DocumentLine:
    kw.setdefault("line_id", line_id or None)
    kw.setdefault("raw_text", raw_text)
    if kw["line_id"] is None:
        del kw["line_id"]  # let default factory generate UUID
    return DocumentLine(**kw)


def _doc(*line_specs) -> Document:
    """Quick document builder: _doc(("id","text"), ...)"""
    lines = [_line(lid, txt) for lid, txt in line_specs]
    return Document(DocumentType.AF, lines=lines)


def _ids(doc: Document) -> list[str]:
    """Return all line_ids in order."""
    return [l.line_id for l in doc.lines]


def _texts(doc: Document) -> list[str]:
    """Return all raw_text in order."""
    return [l.raw_text for l in doc.lines]


def _dummy_parse_fn(raw_text: str) -> DocumentLine:
    """Simulates a full parse returning a fresh DocumentLine."""
    return DocumentLine(raw_text=raw_text, validation_result=ValidationResult())


# ===========================================================
# UndoRedoStack
# ===========================================================

class TestUndoRedoStack:

    def test_empty_stack(self):
        stack = UndoRedoStack()
        assert not stack.can_undo
        assert not stack.can_redo

    def test_undo_empty_raises(self):
        stack = UndoRedoStack()
        with pytest.raises(IndexError, match="Nothing to undo"):
            stack.undo()

    def test_redo_empty_raises(self):
        stack = UndoRedoStack()
        with pytest.raises(IndexError, match="Nothing to redo"):
            stack.redo()

    def test_execute_enables_undo(self):
        stack = UndoRedoStack()
        doc = _doc(("a", "hello"))
        cmd = AppendLineCommand(doc, _line("b", "world"))
        stack.execute(cmd)
        assert stack.can_undo
        assert not stack.can_redo

    def test_undo_enables_redo(self):
        stack = UndoRedoStack()
        doc = _doc()
        cmd = AppendLineCommand(doc, _line("x", "first"))
        stack.execute(cmd)
        stack.undo()
        assert not stack.can_undo
        assert stack.can_redo

    def test_execute_after_undo_clears_redo(self):
        stack = UndoRedoStack()
        doc = _doc()
        stack.execute(AppendLineCommand(doc, _line("a", "one")))
        stack.execute(AppendLineCommand(doc, _line("b", "two")))
        stack.undo()
        assert stack.can_redo
        stack.execute(AppendLineCommand(doc, _line("c", "three")))
        assert not stack.can_redo

    def test_clear(self):
        stack = UndoRedoStack()
        doc = _doc()
        stack.execute(AppendLineCommand(doc, _line("a", "one")))
        stack.undo()
        assert stack.can_redo
        stack.clear()
        assert not stack.can_undo
        assert not stack.can_redo

    def test_multiple_undo_redo_cycle(self):
        stack = UndoRedoStack()
        doc = _doc()
        stack.execute(AppendLineCommand(doc, _line("a", "one")))
        stack.execute(AppendLineCommand(doc, _line("b", "two")))
        assert len(doc) == 2

        stack.undo()
        assert len(doc) == 1
        stack.undo()
        assert len(doc) == 0

        stack.redo()
        assert len(doc) == 1
        stack.redo()
        assert len(doc) == 2


# ===========================================================
# AppendLineCommand
# ===========================================================

class TestAppendLineCommand:

    def test_execute(self):
        doc = _doc()
        cmd = AppendLineCommand(doc, _line("x", "new"))
        cmd.execute()
        assert len(doc) == 1
        assert doc[0].line_id == "x"

    def test_undo(self):
        doc = _doc()
        cmd = AppendLineCommand(doc, _line("x", "new"))
        cmd.execute()
        cmd.undo()
        assert len(doc) == 0

    def test_undo_redo_round_trip(self):
        doc = _doc(("a", "first"))
        cmd = AppendLineCommand(doc, _line("b", "second"))
        cmd.execute()
        assert _ids(doc) == ["a", "b"]
        cmd.undo()
        assert _ids(doc) == ["a"]
        cmd.execute()
        assert _ids(doc) == ["a", "b"]


# ===========================================================
# InsertLineCommand
# ===========================================================

class TestInsertLineCommand:

    def test_execute(self):
        doc = _doc(("a", "first"), ("b", "second"))
        cmd = InsertLineCommand(doc, 1, _line("m", "middle"))
        cmd.execute()
        assert _ids(doc) == ["a", "m", "b"]

    def test_undo(self):
        doc = _doc(("a", "first"), ("b", "second"))
        cmd = InsertLineCommand(doc, 1, _line("m", "middle"))
        cmd.execute()
        cmd.undo()
        assert _ids(doc) == ["a", "b"]

    def test_insert_at_beginning(self):
        doc = _doc(("a", "first"))
        cmd = InsertLineCommand(doc, 0, _line("z", "zero"))
        cmd.execute()
        assert doc[0].line_id == "z"
        cmd.undo()
        assert doc[0].line_id == "a"


# ===========================================================
# RemoveLineCommand
# ===========================================================

class TestRemoveLineCommand:

    def test_execute(self):
        doc = _doc(("a", "first"), ("b", "second"), ("c", "third"))
        cmd = RemoveLineCommand(doc, "b")
        cmd.execute()
        assert _ids(doc) == ["a", "c"]

    def test_undo_restores_at_original_position(self):
        doc = _doc(("a", "first"), ("b", "second"), ("c", "third"))
        cmd = RemoveLineCommand(doc, "b")
        cmd.execute()
        cmd.undo()
        assert _ids(doc) == ["a", "b", "c"]
        assert doc.get_position("b") == 1

    def test_undo_redo_round_trip(self):
        doc = _doc(("a", "first"), ("b", "second"))
        cmd = RemoveLineCommand(doc, "a")
        cmd.execute()
        assert _ids(doc) == ["b"]
        cmd.undo()
        assert _ids(doc) == ["a", "b"]
        cmd.execute()
        assert _ids(doc) == ["b"]


# ===========================================================
# ReplaceLineCommand
# ===========================================================

class TestReplaceLineCommand:

    def test_execute(self):
        doc = _doc(("a", "old"), ("b", "other"))
        new_line = _line("a", "new")
        cmd = ReplaceLineCommand(doc, "a", new_line)
        cmd.execute()
        assert doc[0].raw_text == "new"

    def test_undo_restores_old_line(self):
        doc = _doc(("a", "old"), ("b", "other"))
        new_line = _line("a", "new")
        cmd = ReplaceLineCommand(doc, "a", new_line)
        cmd.execute()
        cmd.undo()
        assert doc[0].raw_text == "old"

    def test_replace_with_different_id(self):
        doc = _doc(("a", "old"), ("b", "other"))
        new_line = _line("z", "replaced")
        cmd = ReplaceLineCommand(doc, "a", new_line)
        cmd.execute()
        assert doc[0].line_id == "z"
        cmd.undo()
        assert doc[0].line_id == "a"
        assert doc[0].raw_text == "old"


# ===========================================================
# SwapLinesCommand
# ===========================================================

class TestSwapLinesCommand:

    def test_swap_down(self):
        doc = _doc(("a", "first"), ("b", "second"), ("c", "third"))
        cmd = SwapLinesCommand(doc, "a", "down")
        cmd.execute()
        assert _ids(doc) == ["b", "a", "c"]

    def test_swap_up(self):
        doc = _doc(("a", "first"), ("b", "second"), ("c", "third"))
        cmd = SwapLinesCommand(doc, "c", "up")
        cmd.execute()
        assert _ids(doc) == ["a", "c", "b"]

    def test_swap_down_boundary_raises(self):
        doc = _doc(("a", "first"), ("b", "second"))
        cmd = SwapLinesCommand(doc, "b", "down")
        with pytest.raises(IndexError, match="boundary"):
            cmd.execute()

    def test_swap_up_boundary_raises(self):
        doc = _doc(("a", "first"), ("b", "second"))
        cmd = SwapLinesCommand(doc, "a", "up")
        with pytest.raises(IndexError, match="boundary"):
            cmd.execute()

    def test_invalid_direction_raises(self):
        doc = _doc(("a", "first"))
        with pytest.raises(ValueError, match="direction"):
            SwapLinesCommand(doc, "a", "left")

    def test_undo(self):
        doc = _doc(("a", "first"), ("b", "second"), ("c", "third"))
        cmd = SwapLinesCommand(doc, "b", "down")
        cmd.execute()
        assert _ids(doc) == ["a", "c", "b"]
        cmd.undo()
        assert _ids(doc) == ["a", "b", "c"]

    def test_undo_redo_round_trip(self):
        doc = _doc(("a", "first"), ("b", "second"))
        cmd = SwapLinesCommand(doc, "a", "down")
        cmd.execute()
        assert _ids(doc) == ["b", "a"]
        cmd.undo()
        assert _ids(doc) == ["a", "b"]
        cmd.execute()
        assert _ids(doc) == ["b", "a"]

    def test_preserves_raw_text(self):
        doc = _doc(("a", "first"), ("b", "second"))
        cmd = SwapLinesCommand(doc, "a", "down")
        cmd.execute()
        assert doc[0].raw_text == "second"
        assert doc[1].raw_text == "first"


class TestDocumentSwapLines:
    """Tests for the Document.swap_lines method itself."""

    def test_swap(self):
        doc = _doc(("a", "first"), ("b", "second"))
        doc.swap_lines("a", "b")
        assert _ids(doc) == ["b", "a"]

    def test_swap_missing_raises(self):
        doc = _doc(("a", "first"))
        with pytest.raises(KeyError):
            doc.swap_lines("a", "missing")


# ===========================================================
# ToggleLineCommentCommand
# ===========================================================

class TestToggleLineCommentCommand:

    def test_comment_a_data_line(self):
        doc = _doc(("a", "some data"))
        cmd = ToggleLineCommentCommand(doc, ["a"], _dummy_parse_fn)
        cmd.execute()
        assert doc[0].raw_text == "# some data"
        assert doc[0].status == LineStatus.COMMENT

    def test_comment_preserves_line_id(self):
        doc = _doc(("a", "some data"))
        cmd = ToggleLineCommentCommand(doc, ["a"], _dummy_parse_fn)
        cmd.execute()
        assert doc[0].line_id == "a"

    def test_uncomment_a_comment_line(self):
        comment_line = _line("a", "# some data",
                             validation_result=ValidationResult(status=LineStatus.COMMENT))
        doc = Document(DocumentType.AF, lines=[comment_line])
        cmd = ToggleLineCommentCommand(doc, ["a"], _dummy_parse_fn)
        cmd.execute()
        assert doc[0].raw_text == "some data"
        assert doc[0].status == LineStatus.OK

    def test_uncomment_assigns_new_line_id(self):
        """Uncommenting creates a brand-new line identity."""
        comment_line = _line("a", "# data",
                             validation_result=ValidationResult(status=LineStatus.COMMENT))
        doc = Document(DocumentType.AF, lines=[comment_line])
        cmd = ToggleLineCommentCommand(doc, ["a"], _dummy_parse_fn)
        cmd.execute()
        assert doc[0].line_id != "a"

    def test_uncomment_strips_hash_space(self):
        comment_line = _line("a", "# hello world",
                             validation_result=ValidationResult(status=LineStatus.COMMENT))
        doc = Document(DocumentType.AF, lines=[comment_line])
        cmd = ToggleLineCommentCommand(doc, ["a"], _dummy_parse_fn)
        cmd.execute()
        assert doc[0].raw_text == "hello world"

    def test_uncomment_strips_hash_without_space(self):
        comment_line = _line("a", "#hello",
                             validation_result=ValidationResult(status=LineStatus.COMMENT))
        doc = Document(DocumentType.AF, lines=[comment_line])
        cmd = ToggleLineCommentCommand(doc, ["a"], _dummy_parse_fn)
        cmd.execute()
        assert doc[0].raw_text == "hello"

    def test_undo_comment(self):
        doc = _doc(("a", "some data"))
        cmd = ToggleLineCommentCommand(doc, ["a"], _dummy_parse_fn)
        cmd.execute()
        cmd.undo()
        assert doc[0].raw_text == "some data"
        assert doc[0].line_id == "a"

    def test_undo_uncomment_restores_comment_status(self):
        comment_line = _line("a", "# data",
                             validation_result=ValidationResult(status=LineStatus.COMMENT))
        doc = Document(DocumentType.AF, lines=[comment_line])
        cmd = ToggleLineCommentCommand(doc, ["a"], _dummy_parse_fn)
        cmd.execute()
        cmd.undo()
        assert doc[0].line_id == "a"
        assert doc[0].status == LineStatus.COMMENT
        assert doc[0].raw_text == "# data"

    def test_redo_after_undo(self):
        doc = _doc(("a", "data"))
        cmd = ToggleLineCommentCommand(doc, ["a"], _dummy_parse_fn)
        cmd.execute()
        commented_text = doc[0].raw_text
        cmd.undo()
        cmd.execute()  # redo
        assert doc[0].raw_text == commented_text

    def test_redo_uncomment_reuses_same_line_id(self):
        """Redo must produce the exact same line_id as the first execute."""
        comment_line = _line("a", "# data",
                             validation_result=ValidationResult(status=LineStatus.COMMENT))
        doc = Document(DocumentType.AF, lines=[comment_line])
        cmd = ToggleLineCommentCommand(doc, ["a"], _dummy_parse_fn)
        cmd.execute()
        new_id = doc[0].line_id
        cmd.undo()
        cmd.execute()  # redo
        assert doc[0].line_id == new_id

    def test_multiple_lines(self):
        doc = _doc(("a", "line1"), ("b", "line2"), ("c", "line3"))
        cmd = ToggleLineCommentCommand(doc, ["a", "c"], _dummy_parse_fn)
        cmd.execute()
        assert doc[0].raw_text == "# line1"
        assert doc[1].raw_text == "line2"  # untouched
        assert doc[2].raw_text == "# line3"

    def test_multiple_lines_undo(self):
        doc = _doc(("a", "line1"), ("b", "line2"), ("c", "line3"))
        cmd = ToggleLineCommentCommand(doc, ["a", "c"], _dummy_parse_fn)
        cmd.execute()
        cmd.undo()
        assert _texts(doc) == ["line1", "line2", "line3"]

    def test_round_trip_comment_uncomment_produces_new_identity(self):
        """
        Comment then uncomment — the uncommented line must be treated
        as completely new (fresh line_id, fresh validation).
        """
        warning_vr = ValidationResult(warnings=["some warning"])
        original = _line("a", "data", validation_result=warning_vr)
        doc = Document(DocumentType.AF, lines=[original])

        # Comment the line
        comment_cmd = ToggleLineCommentCommand(doc, ["a"], _dummy_parse_fn)
        comment_cmd.execute()
        assert doc[0].status == LineStatus.COMMENT

        # Uncomment the line
        uncomment_cmd = ToggleLineCommentCommand(doc, ["a"], _dummy_parse_fn)
        uncomment_cmd.execute()
        # Must have a new identity and fresh status (no stale warning)
        assert doc[0].line_id != "a"
        assert doc[0].status == LineStatus.OK
        assert doc[0].validation_result.warnings == []


# ===========================================================
# Integration: commands with UndoRedoStack
# ===========================================================

class TestCommandsWithStack:

    def test_append_undo_redo_via_stack(self):
        stack = UndoRedoStack()
        doc = _doc()
        stack.execute(AppendLineCommand(doc, _line("a", "first")))
        stack.execute(AppendLineCommand(doc, _line("b", "second")))
        assert len(doc) == 2

        stack.undo()
        assert _ids(doc) == ["a"]
        stack.redo()
        assert _ids(doc) == ["a", "b"]

    def test_mixed_commands_via_stack(self):
        stack = UndoRedoStack()
        doc = _doc(("a", "first"), ("b", "second"))

        # Replace line a
        new_a = _line("a", "modified")
        stack.execute(ReplaceLineCommand(doc, "a", new_a))
        assert doc[0].raw_text == "modified"

        # Insert line at position 1
        stack.execute(InsertLineCommand(doc, 1, _line("m", "middle")))
        assert _ids(doc) == ["a", "m", "b"]

        # Undo insert
        stack.undo()
        assert _ids(doc) == ["a", "b"]

        # Undo replace
        stack.undo()
        assert doc[0].raw_text == "first"

    def test_swap_via_stack(self):
        stack = UndoRedoStack()
        doc = _doc(("a", "first"), ("b", "second"), ("c", "third"))

        stack.execute(SwapLinesCommand(doc, "a", "down"))
        assert _ids(doc) == ["b", "a", "c"]

        stack.undo()
        assert _ids(doc) == ["a", "b", "c"]

        stack.redo()
        assert _ids(doc) == ["b", "a", "c"]

    def test_toggle_comment_via_stack(self):
        stack = UndoRedoStack()
        doc = _doc(("a", "data line"))

        stack.execute(ToggleLineCommentCommand(doc, ["a"], _dummy_parse_fn))
        assert doc[0].status == LineStatus.COMMENT

        stack.undo()
        assert doc[0].raw_text == "data line"

        stack.redo()
        assert doc[0].status == LineStatus.COMMENT
