"""
Tests for io/document_io.py — load / save / parse_line.

Uses tmp_path (pytest built-in) for file system operations.
"""
import gzip

import pytest

from core import DocumentType, LineStatus
from doc_types.af import AfLineData
from doc_types.mutex import MutexLineData
from infrastructure import parse_line, load_document, save_document


# ===========================================================
# parse_line — AF
# ===========================================================

class TestParseLineAf:

    def test_comment(self):
        line = parse_line("# some comment", DocumentType.AF)
        assert line.status == LineStatus.COMMENT
        assert line.data is None

    def test_empty(self):
        line = parse_line("", DocumentType.AF)
        assert line.status == LineStatus.OK

    def test_whitespace_only(self):
        line = parse_line("   ", DocumentType.AF)
        assert line.status == LineStatus.OK

    def test_valid_data(self):
        line = parse_line("{vdd} 0.5 net-regular_em_sh", DocumentType.AF)
        assert line.status == LineStatus.OK
        assert isinstance(line.data, AfLineData)
        assert line.data.net == "vdd"
        assert line.data.af_value == 0.5

    def test_parse_error(self):
        line = parse_line("not a valid line at all", DocumentType.AF)
        assert line.status == LineStatus.ERROR
        assert line.validation_result.errors

    def test_each_line_gets_unique_id(self):
        a = parse_line("# a", DocumentType.AF)
        b = parse_line("# b", DocumentType.AF)
        assert a.line_id != b.line_id


# ===========================================================
# parse_line — Mutex
# ===========================================================

class TestParseLineMutex:

    def test_comment(self):
        line = parse_line("# mutex comment", DocumentType.MUTEX)
        assert line.status == LineStatus.COMMENT

    def test_valid_data(self):
        line = parse_line("mutex2 regular net1 net2", DocumentType.MUTEX)
        assert line.status == LineStatus.OK
        assert isinstance(line.data, MutexLineData)
        assert line.data.num_active == 2
        assert line.data.mutexed_nets == ("net1", "net2")

    def test_parse_error(self):
        line = parse_line("this is garbage", DocumentType.MUTEX)
        assert line.status == LineStatus.ERROR
        assert line.validation_result.errors


# ===========================================================
# load_document — AF file
# ===========================================================

class TestLoadDocumentAf:

    def test_load_basic(self, tmp_path):
        cfg = tmp_path / "test.af"
        cfg.write_text(
            "# header\n"
            "{vdd} 0.5 net-regular_em\n"
            "\n"
            "{gnd} 0.8 net-regular_sh\n"
        )
        doc = load_document(cfg, DocumentType.AF)
        assert len(doc) == 4
        assert doc[0].status == LineStatus.COMMENT
        assert doc[1].status == LineStatus.OK
        assert doc[2].status == LineStatus.OK
        assert doc[3].status == LineStatus.OK
        assert doc.file_path == str(cfg)
        assert doc.doc_type == DocumentType.AF

    def test_load_preserves_error_lines(self, tmp_path):
        cfg = tmp_path / "bad.af"
        cfg.write_text("garbage line\n{vdd} 0.5 net-regular_em\n")
        doc = load_document(cfg, DocumentType.AF)
        assert doc[0].status == LineStatus.ERROR
        assert doc[0].raw_text == "garbage line"
        assert doc[1].status == LineStatus.OK


# ===========================================================
# load_document — Mutex file
# ===========================================================

class TestLoadDocumentMutex:

    def test_load_basic(self, tmp_path):
        cfg = tmp_path / "test.mutex"
        cfg.write_text(
            "# mutex file\n"
            "mutex2 regular net1 net2\n"
        )
        doc = load_document(cfg, DocumentType.MUTEX)
        assert len(doc) == 2
        assert doc[0].status == LineStatus.COMMENT
        assert doc[1].status == LineStatus.OK
        assert doc[1].data.mutexed_nets == ("net1", "net2")


# ===========================================================
# save_document
# ===========================================================

class TestSaveDocument:

    def test_save_round_trip_af(self, tmp_path):
        cfg = tmp_path / "roundtrip.af"
        content = "# header\n{vdd} 0.5 net-regular_em_sh\n\n"
        cfg.write_text(content)

        doc = load_document(cfg, DocumentType.AF)
        out = tmp_path / "output.af"
        save_document(doc, out)
        saved = out.read_text()

        # Comments and blanks are preserved as-is
        lines = saved.splitlines()
        assert lines[0] == "# header"  # Comment line
        assert lines[2] == ""  # Blank line

    def test_save_preserves_error_lines(self, tmp_path):
        cfg = tmp_path / "errors.af"
        cfg.write_text("garbage\n{vdd} 0.5 net-regular_em\n")

        doc = load_document(cfg, DocumentType.AF)
        out = tmp_path / "output.af"
        save_document(doc, out)
        saved = out.read_text()

        lines = saved.strip().split("\n")
        assert lines[0] == "garbage"  # error line preserved verbatim

    def test_save_to_document_path(self, tmp_path):
        cfg = tmp_path / "auto.af"
        cfg.write_text("# test\n")

        doc = load_document(cfg, DocumentType.AF)
        # Modify and save back without explicit path
        save_document(doc)
        assert cfg.read_text().strip() == "# test"

    def test_save_mutex_round_trip(self, tmp_path):
        cfg = tmp_path / "roundtrip.mutex"
        cfg.write_text("# header\nmutex2 regular net1 net2\n")

        doc = load_document(cfg, DocumentType.MUTEX)
        out = tmp_path / "output.mutex"
        save_document(doc, out)
        saved = out.read_text()

        lines = saved.strip().split("\n")
        assert lines[0] == "# header"  # Comment line
        assert "mutex2" in lines[1]
        assert "net1" in lines[1]


# ===========================================================
# gzip support
# ===========================================================

class TestGzipSupport:

    def test_load_gz_file(self, tmp_path):
        cfg = tmp_path / "test.af.gz"
        content = "# header\n{vdd} 0.5 net-regular_em\n"
        with gzip.open(cfg, "wt", encoding="utf-8") as f:
            f.write(content)

        doc = load_document(cfg, DocumentType.AF)
        assert len(doc) == 2
        assert doc[0].status is LineStatus.COMMENT
        assert doc[1].status is LineStatus.OK

    def test_save_gz_file(self, tmp_path):
        cfg = tmp_path / "input.af"
        cfg.write_text("# header\n{vdd} 0.5 net-regular_em\n")
        doc = load_document(cfg, DocumentType.AF)

        out = tmp_path / "output.af.gz"
        save_document(doc, out)

        with gzip.open(out, "rt", encoding="utf-8") as f:
            saved = f.read()
        lines = saved.strip().split("\n")
        assert lines[0] == "# header"

    def test_gz_round_trip(self, tmp_path):
        cfg = tmp_path / "roundtrip.af.gz"
        content = "# comment\n{gnd} 0.8 net-regular_sh\n"
        with gzip.open(cfg, "wt", encoding="utf-8") as f:
            f.write(content)

        doc = load_document(cfg, DocumentType.AF)
        save_document(doc)  # saves back to same gz path

        with gzip.open(cfg, "rt", encoding="utf-8") as f:
            saved = f.read()
        lines = saved.strip().split("\n")
        assert lines[0] == "# comment"
        assert doc[1].data.net == "gnd"
