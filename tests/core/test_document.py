import pytest

from core import Document, DocumentLine, DocumentType


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
