import pytest

from core import Document, DocumentLine, DocumentType
from core.document import MutationRecord


def _make_line(**overrides) -> DocumentLine:
    return DocumentLine(**overrides)


# ===========================================================
# Construction
# ===========================================================

class TestDocumentConstruction:

    def test_empty_document(self):
        doc = Document(DocumentType.AF)
        assert len(doc) == 0
        assert not doc.lines

    def test_from_lines(self):
        lines = [_make_line(raw_text="# comment")]
        doc = Document(DocumentType.AF, lines=lines)
        assert len(doc) == 1
        assert doc[0].raw_text == "# comment"

    def test_file_path(self):
        doc = Document(DocumentType.MUTEX, file_path="/tmp/test.cfg")
        assert doc.file_path == "/tmp/test.cfg"


# ===========================================================
# Read access
# ===========================================================

class TestDocumentRead:

    @pytest.fixture
    def doc(self):
        lines = [
            _make_line(line_id="aaa", raw_text="# first"),
            _make_line(line_id="bbb", raw_text="data line"),
            _make_line(line_id="ccc", raw_text=""),
        ]
        return Document(DocumentType.AF, lines=lines)

    def test_get_line_by_id(self, doc):
        line = doc.get_line("bbb")
        assert line.raw_text == "data line"

    def test_get_position(self, doc):
        assert doc.get_position("aaa") == 0
        assert doc.get_position("ccc") == 2

    def test_has_line(self, doc):
        assert doc.has_line("bbb")
        assert not doc.has_line("zzz")

    def test_getitem(self, doc):
        assert doc[1].line_id == "bbb"

    def test_len(self, doc):
        assert len(doc) == 3

    def test_lines_returns_immutable_view(self, doc):
        """Returned tuple cannot mutate the document's internal state."""
        view = doc.lines
        assert isinstance(view, tuple)
        assert len(view) == len(doc)

    def test_get_line_missing_raises(self, doc):
        with pytest.raises(KeyError):
            doc.get_line("missing")


# ===========================================================
# Mutations
# ===========================================================

class TestDocumentAppend:

    def test_append(self):
        doc = Document(DocumentType.AF)
        line = _make_line(line_id="x1", raw_text="hello")
        doc.append_line(line)
        assert len(doc) == 1
        assert doc.get_line("x1").raw_text == "hello"

    def test_append_duplicate_raises(self):
        doc = Document(DocumentType.AF)
        line = _make_line(line_id="x1")
        doc.append_line(line)
        with pytest.raises(ValueError, match="Duplicate"):
            doc.append_line(_make_line(line_id="x1"))


class TestDocumentInsert:

    def test_insert_at_beginning(self):
        doc = Document(DocumentType.AF, lines=[
            _make_line(line_id="a"),
            _make_line(line_id="b"),
        ])
        new = _make_line(line_id="z", raw_text="inserted")
        doc.insert_line(0, new)
        assert doc[0].line_id == "z"
        assert doc[1].line_id == "a"
        assert doc.get_position("z") == 0
        assert doc.get_position("a") == 1

    def test_insert_at_middle(self):
        doc = Document(DocumentType.AF, lines=[
            _make_line(line_id="a"),
            _make_line(line_id="b"),
        ])
        doc.insert_line(1, _make_line(line_id="m"))
        assert doc[1].line_id == "m"
        assert doc[2].line_id == "b"

    def test_insert_duplicate_raises(self):
        doc = Document(DocumentType.AF, lines=[_make_line(line_id="a")])
        with pytest.raises(ValueError, match="Duplicate"):
            doc.insert_line(0, _make_line(line_id="a"))


class TestDocumentRemove:

    def test_remove(self):
        doc = Document(DocumentType.AF, lines=[
            _make_line(line_id="a"),
            _make_line(line_id="b"),
            _make_line(line_id="c"),
        ])
        removed = doc.remove_line("b")
        assert removed.line_id == "b"
        assert len(doc) == 2
        assert doc.get_position("c") == 1

    def test_remove_missing_raises(self):
        doc = Document(DocumentType.AF)
        with pytest.raises(KeyError):
            doc.remove_line("nope")


class TestDocumentReplace:

    def test_replace_same_id(self):
        doc = Document(DocumentType.AF, lines=[
            _make_line(line_id="a", raw_text="old"),
            _make_line(line_id="b"),
        ])
        replacement = _make_line(line_id="a", raw_text="new")
        doc.replace_line("a", replacement)
        assert doc[0].raw_text == "new"
        assert doc.get_position("a") == 0

    def test_replace_different_id(self):
        doc = Document(DocumentType.AF, lines=[
            _make_line(line_id="a"),
            _make_line(line_id="b"),
        ])
        replacement = _make_line(line_id="z", raw_text="replaced")
        doc.replace_line("a", replacement)
        assert doc[0].line_id == "z"
        assert not doc.has_line("a")
        assert doc.get_position("z") == 0

    def test_replace_missing_raises(self):
        doc = Document(DocumentType.AF)
        with pytest.raises(KeyError):
            doc.replace_line("nope", _make_line())


# ===========================================================
# Undo / Redo
# ===========================================================

class TestUndoRedoProperties:

    def test_fresh_document_has_nothing_to_undo_or_redo(self):
        doc = Document(DocumentType.AF, lines=[_make_line(line_id="a")])
        assert not doc.can_undo
        assert not doc.can_redo

    def test_undo_on_empty_stack_returns_none(self):
        doc = Document(DocumentType.AF)
        assert doc.undo() is None

    def test_redo_on_empty_stack_returns_none(self):
        doc = Document(DocumentType.AF)
        assert doc.redo() is None

    def test_new_mutation_clears_redo_stack(self):
        doc = Document(DocumentType.AF, lines=[
            _make_line(line_id="a", raw_text="original"),
        ])
        new = _make_line(line_id="a", raw_text="edited")
        doc.replace_line("a", new)
        doc.undo()
        assert doc.can_redo
        # A new mutation clears the redo stack
        doc.insert_line(1, _make_line(line_id="z"))
        assert not doc.can_redo


class TestUndoInsert:

    def test_undo_insert_removes_line(self):
        doc = Document(DocumentType.AF, lines=[_make_line(line_id="a")])
        inserted = _make_line(line_id="b", raw_text="new")
        doc.insert_line(1, inserted)
        assert len(doc) == 2

        record = doc.undo()
        assert record is not None
        assert record.kind == "remove"
        assert record.line_id == "b"
        assert record.old_line == inserted
        assert len(doc) == 1
        assert not doc.has_line("b")

    def test_redo_insert_restores_line(self):
        doc = Document(DocumentType.AF, lines=[_make_line(line_id="a")])
        inserted = _make_line(line_id="b", raw_text="new")
        doc.insert_line(1, inserted)
        doc.undo()

        record = doc.redo()
        assert record is not None
        assert record.kind == "insert"
        assert record.line_id == "b"
        assert record.new_line == inserted
        assert len(doc) == 2
        assert doc[1].line_id == "b"


class TestUndoRemove:

    def test_undo_remove_restores_line(self):
        doc = Document(DocumentType.AF, lines=[
            _make_line(line_id="a"),
            _make_line(line_id="b", raw_text="middle"),
            _make_line(line_id="c"),
        ])
        doc.remove_line("b")
        assert len(doc) == 2

        record = doc.undo()
        assert record is not None
        assert record.kind == "insert"
        assert record.line_id == "b"
        assert record.position == 1
        assert len(doc) == 3
        assert doc[1].raw_text == "middle"

    def test_redo_remove_removes_again(self):
        doc = Document(DocumentType.AF, lines=[
            _make_line(line_id="a"),
            _make_line(line_id="b"),
        ])
        doc.remove_line("b")
        doc.undo()
        assert len(doc) == 2

        record = doc.redo()
        assert record.kind == "remove"
        assert record.line_id == "b"
        assert len(doc) == 1


class TestUndoReplace:

    def test_undo_replace_restores_old_line(self):
        doc = Document(DocumentType.AF, lines=[
            _make_line(line_id="a", raw_text="old"),
        ])
        new_line = _make_line(line_id="a", raw_text="new")
        doc.replace_line("a", new_line)
        assert doc[0].raw_text == "new"

        record = doc.undo()
        assert record is not None
        assert record.kind == "replace"
        assert record.line_id == "a"
        assert record.new_line.raw_text == "old"
        assert doc[0].raw_text == "old"

    def test_redo_replace_reapplies(self):
        doc = Document(DocumentType.AF, lines=[
            _make_line(line_id="a", raw_text="old"),
        ])
        new_line = _make_line(line_id="a", raw_text="new")
        doc.replace_line("a", new_line)
        doc.undo()
        assert doc[0].raw_text == "old"

        record = doc.redo()
        assert record.kind == "replace"
        assert doc[0].raw_text == "new"


class TestUndoMultipleOperations:

    def test_multiple_undo_redo_cycle(self):
        doc = Document(DocumentType.AF, lines=[
            _make_line(line_id="a", raw_text="first"),
        ])
        # Insert two lines
        doc.insert_line(1, _make_line(line_id="b", raw_text="second"))
        doc.insert_line(2, _make_line(line_id="c", raw_text="third"))
        assert len(doc) == 3

        # Undo both
        doc.undo()
        assert len(doc) == 2
        doc.undo()
        assert len(doc) == 1
        assert doc[0].raw_text == "first"

        # Redo both
        doc.redo()
        assert len(doc) == 2
        doc.redo()
        assert len(doc) == 3
        assert doc[1].raw_text == "second"
        assert doc[2].raw_text == "third"

    def test_undo_remove_then_replace(self):
        """Undo a replace, then undo a remove — tests mixed stack."""
        doc = Document(DocumentType.AF, lines=[
            _make_line(line_id="a", raw_text="A"),
            _make_line(line_id="b", raw_text="B"),
        ])
        doc.remove_line("b")
        doc.replace_line("a", _make_line(line_id="a", raw_text="A-edited"))

        # Undo replace first (LIFO)
        r1 = doc.undo()
        assert r1.kind == "replace"
        assert doc[0].raw_text == "A"

        # Then undo remove
        r2 = doc.undo()
        assert r2.kind == "insert"
        assert len(doc) == 2
        assert doc[1].raw_text == "B"

    def test_index_consistency_after_undo_redo(self):
        """Verify get_position works correctly through undo/redo cycles."""
        doc = Document(DocumentType.AF, lines=[
            _make_line(line_id="a"),
            _make_line(line_id="b"),
            _make_line(line_id="c"),
        ])
        doc.remove_line("b")
        assert doc.get_position("c") == 1

        doc.undo()
        assert doc.get_position("b") == 1
        assert doc.get_position("c") == 2

        doc.redo()
        assert not doc.has_line("b")
        assert doc.get_position("c") == 1

    def test_append_does_not_record(self):
        doc = Document(DocumentType.AF)
        doc.append_line(_make_line(line_id="a"))
        assert not doc.can_undo


# ===========================================================
# Swap lines
# ===========================================================

class TestSwapLines:

    @pytest.fixture
    def doc(self):
        return Document(DocumentType.AF, lines=[
            _make_line(line_id="a", raw_text="A"),
            _make_line(line_id="b", raw_text="B"),
            _make_line(line_id="c", raw_text="C"),
        ])

    def test_swap_adjacent(self, doc):
        doc.swap_lines(0, 1)
        assert doc[0].raw_text == "B"
        assert doc[1].raw_text == "A"
        assert doc.get_position("a") == 1
        assert doc.get_position("b") == 0

    def test_swap_non_adjacent(self, doc):
        doc.swap_lines(0, 2)
        assert doc[0].raw_text == "C"
        assert doc[2].raw_text == "A"

    def test_swap_is_recorded(self, doc):
        doc.swap_lines(0, 1)
        assert doc.can_undo

    def test_swap_same_raises(self, doc):
        with pytest.raises(ValueError, match="itself"):
            doc.swap_lines(1, 1)

    def test_swap_out_of_range_raises(self, doc):
        with pytest.raises(IndexError):
            doc.swap_lines(0, 99)

    def test_undo_swap(self, doc):
        doc.swap_lines(0, 1)
        record = doc.undo()
        assert record.kind == "swap"
        assert doc[0].raw_text == "A"
        assert doc[1].raw_text == "B"

    def test_redo_swap(self, doc):
        doc.swap_lines(1, 2)
        doc.undo()
        record = doc.redo()
        assert record.kind == "swap"
        assert doc[1].raw_text == "C"
        assert doc[2].raw_text == "B"

    def test_swap_mutation_record_positions(self, doc):
        doc.swap_lines(0, 2)
        record = doc.undo()
        assert record.position == 0
        assert record.position2 == 2
