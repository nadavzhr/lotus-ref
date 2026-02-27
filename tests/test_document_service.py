"""
Integration tests for DocumentService.

These tests exercise the full load → edit → save round-trip through the
service layer, including conflict detection, session management, and
error handling.  They use MockNetlistQueryService (no real netlist)
and temporary files on disk.
"""
from __future__ import annotations

import os
import tempfile

import pytest

from services.document_service import DocumentService
from core import DocumentType, LineStatus
from tests.mock_nqs import MockNetlistQueryService


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _write_tmp(content: str, suffix: str = ".af.dcfg") -> str:
    """Write *content* to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    return path


AF_LINES = """\
# comment line
{in1} 0.5 net-regular_em_sh
{tpl:n1} 1.0 net-regular_template-regular_em_sh
"""

MUTEX_LINES = """\
# mutex
mutex1_low regular ia1/oa1 ia1/ib/nonpinb on=ia1/ib/nonpinb
"""


@pytest.fixture()
def nqs() -> MockNetlistQueryService:
    """Provide a minimal NQS mock with a few nets configured."""
    m = MockNetlistQueryService()
    m.top_cell = "top"
    m.templates = {"tpl", "top"}
    m.canonical_map = {
        ("in1", "top"): "in1",
        ("in1", None): "in1",
        ("n1", "tpl"): "n1",
        ("ia1/oa1", "top"): "ia1/oa1",
        ("ia1/oa1", None): "ia1/oa1",
        ("ia1/ib/nonpinb", "top"): "ia1/ib/nonpinb",
        ("ia1/ib/nonpinb", None): "ia1/ib/nonpinb",
    }
    m.net_matches = {
        (None, "in1", False): ["in1"],
        ("tpl", "n1", False): ["n1"],
    }
    m.instance_names_map = {
        ("tpl", "n1"): {"in1"},
        ("top", "in1"): {"in1"},
    }
    m.nets_in_template = {
        "top": {"in1", "in2"},
        "tpl": {"n1", "n2"},
    }
    return m


@pytest.fixture()
def svc(nqs) -> DocumentService:
    return DocumentService(nqs)


# ==================================================================
# Load & list
# ==================================================================

class TestLoadAndList:
    def test_load_returns_summary(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            result = svc.load("d1", path, DocumentType.AF)
            assert result["doc_id"] == "d1"
            assert result["doc_type"] == "af"
            assert result["total_lines"] > 0
        finally:
            os.unlink(path)

    def test_list_documents_after_load(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            docs = svc.list_documents()
            assert len(docs) == 1
            assert docs[0]["doc_id"] == "d1"
        finally:
            os.unlink(path)

    def test_load_mutex(self, svc: DocumentService):
        path = _write_tmp(MUTEX_LINES, suffix=".mutex.dcfg")
        try:
            result = svc.load("m1", path, DocumentType.MUTEX)
            assert result["doc_type"] == "mutex"
            assert result["total_lines"] > 0
        finally:
            os.unlink(path)


# ==================================================================
# Line access
# ==================================================================

class TestLineAccess:
    def test_get_lines_returns_all(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            lines = svc.get_lines("d1")
            # AF_LINES has 3 non-empty lines (comment + 2 data) + trailing empty
            assert len(lines) >= 3
        finally:
            os.unlink(path)

    def test_get_lines_offset_and_limit(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            all_lines = svc.get_lines("d1")
            subset = svc.get_lines("d1", offset=1, limit=1)
            assert len(subset) == 1
            assert subset[0]["position"] == 1
            assert subset[0]["raw_text"] == all_lines[1]["raw_text"]
        finally:
            os.unlink(path)

    def test_get_line_by_position(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            line = svc.get_line("d1", 0)
            assert line["position"] == 0
            assert line["status"] == LineStatus.COMMENT.value
        finally:
            os.unlink(path)

    def test_get_line_has_data_for_data_line(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            line = svc.get_line("d1", 1)  # {in1} 0.5 ...
            assert line["has_data"] is True
            assert "data" in line
        finally:
            os.unlink(path)


# ==================================================================
# Edit round-trip (AF)
# ==================================================================

class TestEditRoundTrip:
    def test_hydrate_from_existing_line(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            result = svc.hydrate_session("d1", 1)
            assert result["doc_type"] == "af"
            assert result["position"] == 1
            assert "data" in result
        finally:
            os.unlink(path)

    def test_hydrate_with_new_fields(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            fields = {
                "template": None,
                "net": "in1",
                "af_value": 0.9,
                "is_em_enabled": True,
                "is_sh_enabled": True,
            }
            result = svc.hydrate_session("d1", 1, fields=fields)
            assert result["data"]["af_value"] == 0.9
        finally:
            os.unlink(path)

    def test_commit_updates_line(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            # Hydrate with new af_value
            svc.hydrate_session("d1", 1, fields={
                "template": None,
                "net": "in1",
                "af_value": 0.75,
                "is_em_enabled": True,
                "is_sh_enabled": True,
            })
            result = svc.commit_edit("d1", 1)
            assert result["has_data"] is True
            # Verify the document line was actually updated
            line = svc.get_line("d1", 1)
            assert line["data"]["af_value"] == 0.75
        finally:
            os.unlink(path)


# ==================================================================
# Save round-trip
# ==================================================================

class TestSaveRoundTrip:
    def test_save_produces_valid_file(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        save_path = _write_tmp("", suffix=".af.dcfg")
        try:
            svc.load("d1", path, DocumentType.AF)
            # Modify a line
            svc.hydrate_session("d1", 1, fields={
                "template": None,
                "net": "in1",
                "af_value": 0.99,
                "is_em_enabled": True,
                "is_sh_enabled": True,
            })
            svc.commit_edit("d1", 1)
            # Save to a new temp file
            svc.save("d1", save_path)

            # Re-load and verify the edited value persisted
            svc2 = DocumentService(MockNetlistQueryService())
            svc2.load("d2", save_path, DocumentType.AF)
            line = svc2.get_line("d2", 1)
            assert line["data"]["af_value"] == 0.99
        finally:
            os.unlink(path)
            if os.path.exists(save_path):
                os.unlink(save_path)

    def test_save_preserves_comments(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        save_path = _write_tmp("", suffix=".af.dcfg")
        try:
            svc.load("d1", path, DocumentType.AF)
            svc.save("d1", save_path)
            with open(save_path, encoding="utf-8") as f:
                first_line = f.readline().rstrip("\n")
            assert first_line.startswith("# ")
        finally:
            os.unlink(path)
            if os.path.exists(save_path):
                os.unlink(save_path)


# ==================================================================
# Conflict detection through the service
# ==================================================================

class TestConflictDetection:
    def test_duplicate_nets_produce_conflict(self, svc: DocumentService):
        """Two AF lines targeting the same net should create a conflict."""
        content = "{in1} 0.5 net-regular_em_sh\n{in1} 0.7 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            svc.load("d1", path, DocumentType.AF)
            lines = svc.get_lines("d1")
            # At least one line should show conflict status
            statuses = [l["status"] for l in lines]
            assert LineStatus.CONFLICT.value in statuses
        finally:
            os.unlink(path)

    def test_no_conflict_for_distinct_nets(self, svc: DocumentService, nqs):
        """Lines targeting different nets should not conflict."""
        nqs.canonical_map[("in2", None)] = "in2"
        nqs.net_matches[(None, "in2", False)] = ["in2"]
        content = "{in1} 0.5 net-regular_em_sh\n{in2} 0.7 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            svc.load("d1", path, DocumentType.AF)
            lines = svc.get_lines("d1")
            statuses = [l["status"] for l in lines]
            assert LineStatus.CONFLICT.value not in statuses
        finally:
            os.unlink(path)

    def test_conflict_info_has_positions(self, svc: DocumentService):
        """Conflict info should report the other line's position."""
        content = "{in1} 0.5 net-regular_em_sh\n{in1} 0.7 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            svc.load("d1", path, DocumentType.AF)
            lines = svc.get_lines("d1")
            conflicts = [l for l in lines if l["conflict_info"] is not None]
            assert len(conflicts) >= 1
            info = conflicts[0]["conflict_info"]
            assert "conflicting_positions" in info
            assert "shared_nets" in info
            assert len(info["shared_nets"]) > 0
        finally:
            os.unlink(path)


# ==================================================================
# Error handling
# ==================================================================

class TestErrorHandling:
    def test_get_document_missing_raises(self, svc: DocumentService):
        with pytest.raises(KeyError):
            svc.get_document("nonexistent")

    def test_load_nonexistent_file_raises(self, svc: DocumentService):
        with pytest.raises((FileNotFoundError, OSError)):
            svc.load("d1", "/nonexistent/path.af.dcfg", DocumentType.AF)

    def test_malformed_line_is_error_status(self, svc: DocumentService):
        """A completely invalid AF line should parse as an error line."""
        content = "this is garbage\n"
        path = _write_tmp(content)
        try:
            svc.load("d1", path, DocumentType.AF)
            line = svc.get_line("d1", 0)
            assert line["status"] == LineStatus.ERROR.value
        finally:
            os.unlink(path)

    def test_mutex_ops_on_af_doc_raises(self, svc: DocumentService):
        """Mutex-specific operations should reject an AF document."""
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            with pytest.raises(ValueError, match="not a MUTEX"):
                svc.mutex_add_mutexed("d1", None, "net", False)
        finally:
            os.unlink(path)


# ==================================================================
# Delete line
# ==================================================================

class TestDeleteLine:
    def test_delete_reduces_line_count(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            before = len(svc.get_lines("d1"))
            svc.delete_line("d1", 1)
            after = len(svc.get_lines("d1"))
            assert after == before - 1
        finally:
            os.unlink(path)

    def test_delete_removes_correct_line(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            target = svc.get_line("d1", 1)["raw_text"]
            svc.delete_line("d1", 1)
            # The line that was at position 2 should now be at position 1
            remaining_texts = [l["raw_text"] for l in svc.get_lines("d1")]
            assert target not in remaining_texts
        finally:
            os.unlink(path)

    def test_delete_clears_conflict(self, svc: DocumentService):
        """Deleting one of two conflicting lines should clear the conflict."""
        content = "{in1} 0.5 net-regular_em_sh\n{in1} 0.7 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            svc.load("d1", path, DocumentType.AF)
            # Both lines should conflict
            lines = svc.get_lines("d1")
            assert any(l["status"] == "conflict" for l in lines)
            # Delete the second line
            svc.delete_line("d1", 1)
            # Remaining line should no longer conflict
            lines = svc.get_lines("d1")
            assert all(l["status"] != "conflict" for l in lines)
        finally:
            os.unlink(path)

    def test_delete_invalid_position_raises(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            with pytest.raises(IndexError):
                svc.delete_line("d1", 999)
        finally:
            os.unlink(path)


# ==================================================================
# Insert blank line
# ==================================================================

class TestInsertBlankLine:
    def test_insert_increases_line_count(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            before = len(svc.get_lines("d1"))
            svc.insert_blank_line("d1", 0)
            after = len(svc.get_lines("d1"))
            assert after == before + 1
        finally:
            os.unlink(path)

    def test_insert_at_position_shifts_others(self, svc: DocumentService):
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            orig_first = svc.get_line("d1", 0)["raw_text"]
            svc.insert_blank_line("d1", 0)
            # Original first line is now at position 1
            assert svc.get_line("d1", 1)["raw_text"] == orig_first
            # New blank line at position 0
            assert svc.get_line("d1", 0)["raw_text"] == ""
        finally:
            os.unlink(path)

    def test_insert_then_edit_round_trip(self, svc: DocumentService):
        """Insert a blank, hydrate with AF fields, commit — line should have data."""
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            svc.insert_blank_line("d1", 0)
            svc.hydrate_session("d1", 0, fields={
                "template": None,
                "net": "in1",
                "af_value": 0.42,
                "is_em_enabled": True,
                "is_sh_enabled": True,
            })
            result = svc.commit_edit("d1", 0)
            assert result["has_data"] is True
            assert result["data"]["af_value"] == 0.42
        finally:
            os.unlink(path)


# ==================================================================
# Undo / Redo (integration through DocumentService)
# ==================================================================

class TestUndoRedo:

    def test_undo_commit_edit_restores_old_line(self, svc: DocumentService):
        """Undo a commit_edit should restore the original raw_text."""
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            # Find a data line (skip comment / blank)
            lines = svc.get_lines("d1")
            data_line = next(l for l in lines if l["has_data"])
            pos = data_line["position"]
            original_raw = data_line["raw_text"]

            # Edit the line
            svc.hydrate_session("d1", pos, fields={
                "template": None,
                "net": "in1",
                "af_value": 0.99,
                "is_em_enabled": True,
                "is_sh_enabled": True,
            })
            svc.commit_edit("d1", pos)
            assert svc.get_line("d1", pos)["raw_text"] != original_raw

            # Undo
            result = svc.undo("d1")
            assert result["action"] == "replace"
            assert result["can_redo"] is True
            assert svc.get_line("d1", pos)["raw_text"] == original_raw
        finally:
            os.unlink(path)

    def test_undo_delete_restores_line(self, svc: DocumentService):
        """Undo a delete_line should restore the removed line."""
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            original_count = svc.get_document("d1").__len__()

            svc.delete_line("d1", 0)
            assert svc.get_document("d1").__len__() == original_count - 1

            result = svc.undo("d1")
            assert result["action"] == "insert"
            assert svc.get_document("d1").__len__() == original_count
        finally:
            os.unlink(path)

    def test_undo_insert_removes_line(self, svc: DocumentService):
        """Undo an insert_blank_line should remove it."""
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            original_count = svc.get_document("d1").__len__()

            svc.insert_blank_line("d1", 0)
            assert svc.get_document("d1").__len__() == original_count + 1

            result = svc.undo("d1")
            assert result["action"] == "remove"
            assert svc.get_document("d1").__len__() == original_count
        finally:
            os.unlink(path)

    def test_redo_after_undo(self, svc: DocumentService):
        """Redo should reapply the undone operation."""
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            svc.insert_blank_line("d1", 0)
            svc.undo("d1")
            original_count = svc.get_document("d1").__len__()

            result = svc.redo("d1")
            assert result["action"] == "insert"
            assert svc.get_document("d1").__len__() == original_count + 1
        finally:
            os.unlink(path)

    def test_undo_nothing_raises(self, svc: DocumentService):
        """Undo on a freshly loaded document should raise ValueError."""
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            with pytest.raises(ValueError, match="Nothing to undo"):
                svc.undo("d1")
        finally:
            os.unlink(path)

    def test_redo_nothing_raises(self, svc: DocumentService):
        """Redo with empty redo stack should raise ValueError."""
        path = _write_tmp(AF_LINES)
        try:
            svc.load("d1", path, DocumentType.AF)
            with pytest.raises(ValueError, match="Nothing to redo"):
                svc.redo("d1")
        finally:
            os.unlink(path)

    def test_summary_includes_undo_redo_flags(self, svc: DocumentService):
        """Document summary should include can_undo / can_redo."""
        path = _write_tmp(AF_LINES)
        try:
            summary = svc.load("d1", path, DocumentType.AF)
            assert summary["can_undo"] is False
            assert summary["can_redo"] is False

            svc.insert_blank_line("d1", 0)
            docs = svc.list_documents()
            assert docs[0]["can_undo"] is True
        finally:
            os.unlink(path)
