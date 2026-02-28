"""
Comprehensive integration test for the MUTEX document type.

Exercises the full document lifecycle without the web server or
DocumentService layer — only Document, Session/Controller, ConflictDetector,
and DocumentIO are used, simulating exactly the operations the frontend
would trigger.

Test flow:
1. Create a MUTEX document with comments, valid lines, warnings, errors,
   and empty lines.  Verify statuses and absence of conflicts.
2. Edit a line via a controller session to introduce a conflict.
   First verify invalid edits (duplicate, regex mismatch, template mismatch)
   produce the expected session errors, then commit a valid edit that overlaps
   with an existing line and verify conflict detection.
3. Resolve the conflict by editing the line again and verify conflicts clear.
4. Document commands: toggle comment, delete a line, insert an empty line.
5. Undo/redo the step-4 commands and verify document state at each point.
6. Save to disk and reload — verify the round-trip is lossless.
"""

from __future__ import annotations

import pytest

from core.document import Document
from core.document_line import DocumentLine
from core.document_type import DocumentType
from core.conflict_store import ConflictDetector
from core.line_status import LineStatus
from core.validation_result import ValidationResult

from doc_types.mutex.controller import MutexEditController
from doc_types.mutex.line_data import MutexLineData, FEVMode
from doc_types.mutex import serializer as mutex_serializer
from doc_types.mutex.exceptions import (
    DuplicateEntryError,
    RegexModeMismatchError,
    TemplateMismatchError,
)

from infrastructure.document_io import parse_line, load_document, save_document
from tests.mock_nqs import MockNetlistQueryService


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _build_nqs() -> MockNetlistQueryService:
    """Pre-configured mock NQS with two templates and several nets."""
    nqs = MockNetlistQueryService()
    nqs.top_cell = "top"
    nqs.templates = {"t1", "t2"}

    # Template t1 — five nets
    for name in ("net1", "net2", "net3", "net4", "net5"):
        nqs.canonical_map[(name, "t1")] = name
        nqs.instance_names_map[("t1", name)] = {f"top/i1/{name}"}

    # Template t2 — three nets
    for name in ("neta", "netb", "netc"):
        nqs.canonical_map[(name, "t2")] = name
        nqs.instance_names_map[("t2", name)] = {f"top/i2/{name}"}

    # Regex resolution for t1
    nqs.net_matches[("t1", "net.*", True)] = ["net1", "net2", "net3", "net4", "net5"]

    # Per-template net sets (used by get_all_nets_in_template)
    nqs.nets_in_template["t1"] = {"net1", "net2", "net3", "net4", "net5"}
    nqs.nets_in_template["t2"] = {"neta", "netb", "netc"}

    return nqs


def _parse(raw_text: str, nqs) -> DocumentLine:
    """Shortcut for parsing a single raw line into a DocumentLine."""
    return parse_line(raw_text, DocumentType.MUTEX, nqs)


def _commit_edit(
    doc: Document,
    detector: ConflictDetector,
    line_id: str,
    new_data: MutexLineData,
    nqs,
) -> None:
    """Serialize new data, create a replacement DocumentLine (preserving
    line_id), replace in the document, and update the conflict index."""
    raw_text = mutex_serializer.serialize(new_data)
    parsed = _parse(raw_text, nqs)
    replacement = DocumentLine(
        line_id=line_id,
        raw_text=parsed.raw_text,
        data=parsed.data,
        validation_result=parsed.validation_result,
    )
    doc.replace_line(line_id, replacement)
    detector.update_line(line_id, replacement.data)


# ------------------------------------------------------------------
# Integration test
# ------------------------------------------------------------------

class TestMutexIntegration:
    """End-to-end MUTEX document flow: create → edit → conflict →
    resolve → commands → undo/redo → save/reload."""

    def test_full_lifecycle(self, tmp_path):
        nqs = _build_nqs()
        detector = ConflictDetector(nqs)

        # ==========================================================
        # STEP 1 — Create document with various line types
        # ==========================================================
        raw_lines = [
            "# This is a mutex config file",               # 0  comment
            "mutex1 template t1 net1 net2 on=net1",        # 1  valid OK
            "",                                             # 2  empty  OK
            "mutex1_low template t1 net3 net4 on=net3",    # 3  valid OK (FEV low)
            "mutex1 template t2 neta netb on=neta",        # 4  valid OK (template t2)
            "# Another comment",                           # 5  comment
            "this is garbage text",                        # 6  error  (unparseable)
            "mutex1 template t3 netx nety on=netx",        # 7  warning (template t3 unknown)
        ]
        doc_lines = [_parse(t, nqs) for t in raw_lines]
        doc = Document(
            doc_type=DocumentType.MUTEX,
            file_path="test.dcfg",
            lines=doc_lines,
        )

        # --- verify count & statuses ---
        assert len(doc) == 8

        assert doc[0].status == LineStatus.COMMENT
        assert doc[0].data is None

        assert doc[1].status == LineStatus.OK
        assert doc[1].data is not None
        assert doc[1].data.template == "t1"
        assert set(doc[1].data.mutexed_nets) == {"net1", "net2"}
        assert doc[1].data.active_nets == ("net1",)

        assert doc[2].status == LineStatus.OK
        assert doc[2].data is None                           # empty line

        assert doc[3].status == LineStatus.OK
        assert doc[3].data is not None
        assert doc[3].data.fev == FEVMode.LOW

        assert doc[4].status == LineStatus.OK
        assert doc[4].data.template == "t2"

        assert doc[5].status == LineStatus.COMMENT

        assert doc[6].status == LineStatus.ERROR
        assert doc[6].validation_result.errors              # has at least one error msg

        assert doc[7].status == LineStatus.WARNING
        assert any("t3" in w for w in doc[7].validation_result.warnings)

        # --- build conflict index — no conflicts yet ---
        detector.rebuild(list(doc.lines))
        for line in doc.lines:
            assert not detector.is_conflicting(line.line_id), (
                f"Line at pos {doc.get_position(line.line_id)} should not conflict"
            )

        # stash stable IDs
        id1 = doc[1].line_id   # template t1, net1+net2
        id3 = doc[3].line_id   # template t1, net3+net4
        id4 = doc[4].line_id   # template t2
        id6 = doc[6].line_id   # error line

        # ==========================================================
        # STEP 2 — Session edits → introduce a conflict
        # ==========================================================

        # -- 2.1.2  Invalid edit A: duplicate entry --
        ctrl = MutexEditController(nqs)
        ctrl.start_session("inv-dup")
        ctrl.from_line_data(doc[3].data)          # loads net3, net4
        with pytest.raises(DuplicateEntryError):
            ctrl.add_mutexed("t1", "net3")        # already present

        # -- 2.1.2  Invalid edit B: regex mode mismatch --
        ctrl_rx = MutexEditController(nqs)
        ctrl_rx.start_session("inv-regex")
        ctrl_rx.add_mutexed("t1", "net1")         # exact mode session
        with pytest.raises(RegexModeMismatchError):
            ctrl_rx.add_mutexed("t1", "net.*", is_regex=True)

        # -- 2.1.2  Invalid edit C: template mismatch --
        ctrl_tpl = MutexEditController(nqs)
        ctrl_tpl.start_session("inv-tpl")
        ctrl_tpl.add_mutexed("t1", "net1")
        with pytest.raises(TemplateMismatchError):
            ctrl_tpl.add_mutexed("t2", "neta")

        # -- 2.1.2  Validation failure: not enough nets --
        ctrl_few = MutexEditController(nqs)
        ctrl_few.start_session("inv-few")
        ctrl_few.add_mutexed("t1", "net1")        # only 1 net
        vr = ctrl_few.validate()
        assert not vr, "Session with only 1 net should fail validation"
        assert any("2" in e for e in vr.errors)

        # -- 2.1.1  Valid edit that creates a conflict --
        # Replace line 3 (net3+net4) with (net1+net5) — net1 overlaps with line 1
        ctrl_cf = MutexEditController(nqs)
        ctrl_cf.start_session("conflict-edit")
        ctrl_cf.set_fev_mode(FEVMode.LOW)
        ctrl_cf.add_mutexed("t1", "net1")
        ctrl_cf.add_mutexed("t1", "net5")
        vr = ctrl_cf.validate()
        assert vr, f"Expected valid, got: {vr.errors}"

        _commit_edit(doc, detector, id3, ctrl_cf.to_line_data(), nqs)

        # Verify conflict between line 1 and line 3
        assert detector.is_conflicting(id1), "Line 1 should now conflict"
        assert detector.is_conflicting(id3), "Line 3 should now conflict"
        assert id3 in detector.get_conflicting_lines(id1)
        assert id1 in detector.get_conflicting_lines(id3)

        # Line 4 (template t2) is unaffected
        assert not detector.is_conflicting(id4)

        # Shared net is "top/i1/net1"
        shared = detector.get_conflicting_net_ids(id1)
        assert shared, "Shared net set must be non-empty"

        # ==========================================================
        # STEP 3 — Resolve the conflict
        # ==========================================================
        # Edit line 3 → (net3, net5) — no overlap with line 1
        ctrl_fix = MutexEditController(nqs)
        ctrl_fix.start_session("resolve")
        ctrl_fix.set_fev_mode(FEVMode.LOW)
        ctrl_fix.add_mutexed("t1", "net3")
        ctrl_fix.add_mutexed("t1", "net5")
        vr = ctrl_fix.validate()
        assert vr, f"Expected valid, got: {vr.errors}"

        _commit_edit(doc, detector, id3, ctrl_fix.to_line_data(), nqs)

        assert not detector.is_conflicting(id1), "Conflict on line 1 should be cleared"
        assert not detector.is_conflicting(id3), "Conflict on line 3 should be cleared"

        # ==========================================================
        # STEP 4 — Document commands
        # ==========================================================

        # 4a  Toggle line 1 to a comment
        old_line1 = doc.get_line(id1)
        assert old_line1.data is not None
        commented = DocumentLine(
            line_id=id1,
            raw_text="# " + mutex_serializer.serialize(old_line1.data),
            data=None,
            validation_result=ValidationResult(status=LineStatus.COMMENT),
        )
        doc.replace_line(id1, commented)
        detector.update_line(id1, None)

        assert doc.get_line(id1).status == LineStatus.COMMENT
        assert not detector.is_conflicting(id1)

        # 4b  Delete the error line (original position 6)
        count_before = len(doc)
        removed = doc.remove_line(id6)
        detector.remove_line(id6)
        assert removed.status == LineStatus.ERROR
        assert len(doc) == count_before - 1
        assert not doc.has_line(id6)

        # 4c  Insert an empty line at the end
        empty_line = DocumentLine(
            raw_text="",
            data=None,
            validation_result=ValidationResult(status=LineStatus.OK),
        )
        doc.insert_line(len(doc), empty_line)
        assert doc[len(doc) - 1].status == LineStatus.OK
        assert doc[len(doc) - 1].raw_text == ""
        empty_id = doc[len(doc) - 1].line_id

        # After step 4: 8 lines (8 – 1 deleted + 1 inserted)
        assert len(doc) == 8

        # ==========================================================
        # STEP 5 — Undo / Redo
        # ==========================================================

        # -- undo insert empty → 7 lines --
        assert doc.can_undo
        rec = doc.undo()
        assert rec is not None and rec.kind == "remove"
        assert len(doc) == 7
        assert not doc.has_line(empty_id)

        # -- undo delete error → 8 lines, error line back --
        rec = doc.undo()
        assert rec is not None and rec.kind == "insert"
        assert len(doc) == 8
        assert doc.has_line(id6)
        assert doc.get_line(id6).status == LineStatus.ERROR

        # -- undo toggle comment → line 1 restored to data --
        rec = doc.undo()
        assert rec is not None and rec.kind == "replace"
        assert doc.get_line(id1).data is not None
        assert doc.get_line(id1).status == LineStatus.OK

        # -- redo toggle → line 1 back to comment --
        assert doc.can_redo
        rec = doc.redo()
        assert rec is not None and rec.kind == "replace"
        assert doc.get_line(id1).status == LineStatus.COMMENT

        # -- redo delete → error line removed again --
        rec = doc.redo()
        assert rec is not None and rec.kind == "remove"
        assert not doc.has_line(id6)

        # -- redo insert empty → 8 lines --
        rec = doc.redo()
        assert rec is not None and rec.kind == "insert"
        assert len(doc) == 8
        assert not doc.can_redo

        # ==========================================================
        # STEP 6 — Save and reload
        # ==========================================================
        save_path = tmp_path / "output.mutex.dcfg"
        save_document(doc, save_path)

        reloaded = load_document(save_path, DocumentType.MUTEX, nqs)
        assert len(reloaded) == len(doc)

        for i, (orig, loaded) in enumerate(zip(doc.lines, reloaded.lines)):
            assert orig.status == loaded.status, (
                f"Line {i}: status {orig.status!r} != {loaded.status!r}"
            )
            if orig.data is not None:
                assert loaded.data is not None, f"Line {i}: expected data, got None"
                # Semantic equality — net order may differ after serialization
                assert orig.data.template == loaded.data.template
                assert orig.data.fev == loaded.data.fev
                assert orig.data.num_active == loaded.data.num_active
                assert orig.data.is_net_regex == loaded.data.is_net_regex
                assert set(orig.data.mutexed_nets) == set(loaded.data.mutexed_nets)
                assert set(orig.data.active_nets) == set(loaded.data.active_nets)
            else:
                assert orig.raw_text == loaded.raw_text, (
                    f"Line {i}: raw_text mismatch"
                )