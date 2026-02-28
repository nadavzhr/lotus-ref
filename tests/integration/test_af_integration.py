"""
This test file is intended for a comprehensive integration test of the entire Lotus system, including the web server and frontend. It should be run manually and is not part of the automated test suite.
It involves no UI, only simulating user interaction through manual invocations of the backend API and inspecting the resulting document state. The goal is to verify that all components of the system work together correctly in a realistic usage scenario, including conflict detection and resolution, line status updates, and frontend display logic.
Test flow:
1. Create a new AF document, add some lines, and verify they are added correctly.
1.1. Some lines are comments, some are valid, some have warnings, and some have errors.
2. Simulate a user editing a line to introduce a conflict, and verify that the conflict is detected and the line status is updated to "conflict".
2.1. The edit is performed via creating a session, making changes, and then committing the session.
2.1.1. The test should modify the session's state via its API to simulate the user making edits in the frontend, rather than directly modifying the document state.
2.1.2. Start by first modifying the session's state with an invalid edit that would cause an error (e.g. no net names, AF VALUE is not between 0 and 1, etc.) and verify that the session's validation returns errors/warnings as expected before committing.
3. Simulate resolving the conflict and verify that the line status updates back to "ok".
4. Execute some document commands such as:
    - Toggling a line's comment status and verifying the status updates accordingly.
    - Deleting a line and verifying it is removed from the document.
    - Adding an empty line and verifying it is added with the correct status.
5. Now test undo/redo functionality by performing some edits and then undoing and redoing them, verifying the document state at each step.
6. Finally save the document and verify that the saved state is correct and can be reloaded without issues.

DO NOT USE DOCUMENT_SERVICE, only interact with the document and session objects directly to simulate user interactions. This is to ensure that we are testing the core logic of the document and session management without any interference from the web server or API layer, which will be tested separately in their own integration tests.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from core import (
    Document,
    DocumentLine,
    DocumentType,
    LineStatus,
    ValidationResult,
    ConflictDetector,
)
from doc_types.af import AfEditController, AfEditSessionState, parser as af_parser, serializer as af_serializer, validator as af_validator
from infrastructure import load_document, save_document, parse_line
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


def _rebuild_and_check_conflicts(
    doc: Document, detector: ConflictDetector,
) -> dict[int, bool]:
    """Rebuild conflicts and return {position: is_conflicting} for every line."""
    detector.rebuild(list(doc.lines))
    return {
        i: detector.is_conflicting(line.line_id)
        for i, line in enumerate(doc.lines)
    }


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture()
def nqs() -> MockNetlistQueryService:
    """
    A MockNetlistQueryService configured with two templates ('top', 'tpl')
    and several nets so that:
      - {in1} resolves normally               (OK)
      - {in2} resolves normally               (OK, distinct from in1)
      - {tpl:n1} resolves normally with
        template-regular (OK, but its canonical top-level instance
        name is 'in1' — used to create cross-template conflicts)
      - any unregistered net matches nothing   (produces a WARNING)
    """
    m = MockNetlistQueryService()
    m.top_cell = "top"
    m.templates = {"tpl", "top"}
    m.canonical_map = {
        ("in1", "top"): "in1",
        ("in1", None): "in1",
        ("in2", "top"): "in2",
        ("in2", None): "in2",
        ("n1", "tpl"): "n1",
    }
    m.net_matches = {
        (None, "in1", False): ["in1"],
        (None, "in2", False): ["in2"],
        ("tpl", "n1", False): ["n1"],
    }
    m.instance_names_map = {
        ("top", "in1"): {"in1"},
        ("top", "in2"): {"in2"},
        ("tpl", "n1"): {"in1"},   # n1 in tpl maps to in1 at top → conflict source
    }
    m.nets_in_template = {
        "top": {"in1", "in2"},
        "tpl": {"n1", "n2"},
    }
    return m


@pytest.fixture()
def detector(nqs) -> ConflictDetector:
    return ConflictDetector(nqs)


@pytest.fixture()
def ctrl(nqs) -> AfEditController:
    return AfEditController(nqs)


# ======================================================================
# Step 1: Create / load an AF document with mixed line types
# ======================================================================

class TestStep1LoadDocumentWithMixedLines:
    """
    Load a document that contains a comment, a valid line, a line with
    warnings, a malformed line, and an empty line. Verify each line's
    status matches expectations.
    """

    def test_load_and_classify_all_line_types(self, nqs):
        content = (
            "# This is a comment\n"
            "{in1} 0.5 net-regular_em_sh\n"
            "{unknown_net} 0.5 net-regular_em_sh\n"
            "this is completely invalid\n"
            "\n"
        )
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)

            assert doc.doc_type == DocumentType.AF
            assert len(doc) == 5

            # Line 0: comment
            assert doc[0].status == LineStatus.COMMENT
            assert doc[0].raw_text.startswith("#")
            assert doc[0].data is None

            # Line 1: valid data ({in1} 0.5)
            assert doc[1].status == LineStatus.OK
            assert doc[1].data is not None
            assert doc[1].data.net == "in1"
            assert doc[1].data.af_value == 0.5

            # Line 2: warning (unknown net — no matches in NQS)
            assert doc[2].status == LineStatus.WARNING
            assert len(doc[2].validation_result.warnings) >= 1
            assert doc[2].data is not None  # parsed OK, just NQS warning

            # Line 3: error (malformed — parse failure)
            assert doc[3].status == LineStatus.ERROR
            assert len(doc[3].validation_result.errors) >= 1
            assert doc[3].data is None

            # Line 4: empty
            assert doc[4].status == LineStatus.OK
            assert doc[4].raw_text == ""
            assert doc[4].data is None
        finally:
            os.unlink(path)

    def test_document_lines_are_addressable_by_id(self, nqs):
        """Each line should be retrievable by its stable UUID."""
        content = "{in1} 0.5 net-regular_em_sh\n{in2} 0.7 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)
            for i, line in enumerate(doc.lines):
                assert doc.get_line(line.line_id) is line
                assert doc.get_position(line.line_id) == i
        finally:
            os.unlink(path)


# ======================================================================
# Step 2: Edit a line via session to introduce a conflict
# ======================================================================

class TestStep2EditSessionAndConflict:
    """
    2.1.2  Hydrate the session with INVALID fields first and verify
           the controller's validation returns errors.
    2.1.1  Then hydrate with valid fields that duplicate a net
           (introducing a conflict) and commit.
    2.     Verify both lines now conflict.
    """

    def test_session_invalid_then_valid_causing_conflict(
        self, nqs, detector, ctrl,
    ):
        # Load two non-conflicting lines
        content = "{in1} 0.5 net-regular_em_sh\n{in2} 0.7 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)
            detector.rebuild(list(doc.lines))

            # Sanity: no conflicts initially
            assert not detector.is_conflicting(doc[0].line_id)
            assert not detector.is_conflicting(doc[1].line_id)

            # --- 2.1.2: Start a session with INVALID data ---
            ctrl.start_session(doc[1].line_id)
            ctrl.set_net("")            # empty net → error
            ctrl.set_af_value(1.5)      # out of range → error
            ctrl.set_em_mode(True)
            ctrl.set_sh_mode(True)

            vr = ctrl.validate()
            assert not vr.is_valid
            assert any("net" in e.lower() for e in vr.errors), \
                f"Expected 'net' error, got: {vr.errors}"
            assert any("af" in e.lower() for e in vr.errors), \
                f"Expected 'af' error, got: {vr.errors}"

            # --- 2.1.1: Now set valid data that duplicates in1 ---
            ctrl.start_session(doc[1].line_id)
            ctrl.set_net("in1")         # same as line 0 → will conflict
            ctrl.set_af_value(0.8)
            ctrl.set_em_mode(True)
            ctrl.set_sh_mode(True)

            vr = ctrl.validate()
            assert vr.is_valid, f"Expected valid, got errors: {vr.errors}"

            # Commit: build new DocumentLine and replace in the document
            committed_data = ctrl.to_line_data()
            raw = af_serializer.serialize(committed_data)
            new_line = DocumentLine(
                line_id=doc[1].line_id,
                raw_text=raw,
                data=committed_data,
                validation_result=vr,
            )
            doc.replace_line(doc[1].line_id, new_line)

            # Update conflict detector for the edited line
            detector.update_line(new_line.line_id, committed_data)

            # --- 2: Both lines now target 'in1' → conflict ---
            assert detector.is_conflicting(doc[0].line_id), \
                "Line 0 should be conflicting after line 1 now targets in1"
            assert detector.is_conflicting(doc[1].line_id), \
                "Line 1 should be conflicting after targeting in1"

            # Peer info should reference the other line
            info_0 = detector.get_conflict_info(doc[0].line_id)
            assert info_0 is not None
            assert doc[1].line_id in info_0.conflicting_line_ids
        finally:
            os.unlink(path)

    def test_session_validates_multiple_errors_simultaneously(
        self, nqs, ctrl,
    ):
        """Multiple domain errors are returned at once."""
        ctrl.start_session("test-session")
        ctrl.set_net("")
        ctrl.set_af_value(-0.1)
        ctrl.set_em_mode(False)
        ctrl.set_sh_mode(False)

        vr = ctrl.validate()
        assert not vr.is_valid
        # All three domain errors should be present
        assert len(vr.errors) >= 3
        error_text = " ".join(vr.errors).lower()
        assert "net" in error_text
        assert "af" in error_text
        assert "em" in error_text or "sh" in error_text


# ======================================================================
# Step 3: Resolve the conflict by editing the duplicate away
# ======================================================================

class TestStep3ResolveConflict:

    def test_resolve_conflict_by_changing_net(self, nqs, detector, ctrl):
        """
        Start with two conflicting lines ({in1} x2), then edit the
        second line to target {in2} and verify the conflict clears.
        """
        content = "{in1} 0.5 net-regular_em_sh\n{in1} 0.7 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)
            detector.rebuild(list(doc.lines))

            assert detector.is_conflicting(doc[0].line_id)
            assert detector.is_conflicting(doc[1].line_id)

            # Edit line 1 to target 'in2' instead
            ctrl.start_session(doc[1].line_id)
            ctrl.set_net("in2")
            ctrl.set_af_value(0.7)
            ctrl.set_em_mode(True)
            ctrl.set_sh_mode(True)

            vr = ctrl.validate()
            assert vr.is_valid

            committed_data = ctrl.to_line_data()
            raw = af_serializer.serialize(committed_data)
            new_line = DocumentLine(
                line_id=doc[1].line_id,
                raw_text=raw,
                data=committed_data,
                validation_result=vr,
            )
            doc.replace_line(doc[1].line_id, new_line)
            detector.update_line(new_line.line_id, committed_data)

            # Both lines should now be conflict-free
            assert not detector.is_conflicting(doc[0].line_id)
            assert not detector.is_conflicting(doc[1].line_id)
        finally:
            os.unlink(path)


# ======================================================================
# Step 4: Document commands — toggle comment, delete, insert blank
# ======================================================================

class TestStep4DocumentCommands:

    def test_toggle_comment_on_data_line(self, nqs, detector):
        """
        Commenting a data line: prepend '# ', set status to COMMENT,
        data becomes None.  Uncommenting: strip '#', re-parse.
        """
        content = "{in1} 0.5 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)
            old_line = doc[0]
            original_raw = old_line.raw_text
            assert old_line.status == LineStatus.OK
            assert old_line.data is not None

            # --- Comment ---
            commented_line = DocumentLine(
                line_id=old_line.line_id,
                raw_text="# " + old_line.raw_text,
                validation_result=ValidationResult(status=LineStatus.COMMENT),
            )
            doc.replace_line(old_line.line_id, commented_line)

            assert doc[0].status == LineStatus.COMMENT
            assert doc[0].raw_text.startswith("# ")
            assert doc[0].data is None

            # Conflict detector: commenting removes the line from net index
            detector.rebuild(list(doc.lines))
            assert not detector.is_conflicting(doc[0].line_id)

            # --- Uncomment ---
            stripped_raw = doc[0].raw_text[2:]  # remove '# '
            uncommented_line = parse_line(stripped_raw, DocumentType.AF, nqs)
            # Preserve the stable line_id
            uncommented_line = DocumentLine(
                line_id=old_line.line_id,
                raw_text=uncommented_line.raw_text,
                data=uncommented_line.data,
                validation_result=uncommented_line.validation_result,
            )
            doc.replace_line(doc[0].line_id, uncommented_line)

            assert doc[0].status in (LineStatus.OK, LineStatus.WARNING)
            assert doc[0].data is not None
            assert doc[0].raw_text == original_raw
        finally:
            os.unlink(path)

    def test_delete_line(self, nqs, detector):
        """Delete a line and verify it is removed and positions shift."""
        content = (
            "# comment\n"
            "{in1} 0.5 net-regular_em_sh\n"
            "{in2} 0.7 net-regular_em_sh\n"
        )
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)
            assert len(doc) == 3
            line1_id = doc[1].line_id

            # Delete line 1
            removed = doc.remove_line(line1_id)
            assert removed.data.net == "in1"
            assert len(doc) == 2

            # The former line 2 is now at position 1
            assert doc[1].data.net == "in2"

            # The removed line_id is no longer in the document
            assert not doc.has_line(line1_id)

            # Conflict detector: removing the line clears it
            detector.remove_line(line1_id)
        finally:
            os.unlink(path)

    def test_insert_empty_line(self, nqs):
        """Insert a blank line and verify it appears with status OK."""
        content = "{in1} 0.5 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)
            assert len(doc) == 1

            blank = DocumentLine(
                raw_text="",
                validation_result=ValidationResult(status=LineStatus.OK),
            )
            doc.insert_line(0, blank)

            assert len(doc) == 2
            assert doc[0].raw_text == ""
            assert doc[0].status == LineStatus.OK
            assert doc[0].data is None

            # Original data line shifted to position 1
            assert doc[1].data is not None
            assert doc[1].data.net == "in1"
        finally:
            os.unlink(path)

    def test_commenting_conflicting_line_clears_conflict(self, nqs, detector):
        """
        Commenting out a conflicting line removes its data, so its
        nets are removed from the conflict store and the peer becomes
        conflict-free.
        """
        content = "{in1} 0.5 net-regular_em_sh\n{in1} 0.7 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)
            detector.rebuild(list(doc.lines))
            assert detector.is_conflicting(doc[0].line_id)

            # Comment out line 1
            old_line = doc[1]
            commented_line = DocumentLine(
                line_id=old_line.line_id,
                raw_text="# " + old_line.raw_text,
                validation_result=ValidationResult(status=LineStatus.COMMENT),
            )
            doc.replace_line(old_line.line_id, commented_line)
            detector.remove_line(old_line.line_id)

            assert not detector.is_conflicting(doc[0].line_id)
            assert doc[1].status == LineStatus.COMMENT
        finally:
            os.unlink(path)


# ======================================================================
# Step 5: Undo / Redo
# ======================================================================

class TestStep5UndoRedo:

    def test_full_undo_redo_lifecycle(self, nqs, ctrl):
        """
        1. Load (2 lines)
        2. Delete line 1          → 1 line
        3. Insert blank at pos 0  → 2 lines
        4. Edit (commit) line 1   → af changed
        5. Undo edit              → af restored
        6. Undo insert            → 1 line
        7. Undo delete            → 2 original lines
        8. Redo delete            → 1 line
        9. Redo insert            → 2 lines
       10. Redo edit              → af changed again
        """
        content = "{in1} 0.5 net-regular_em_sh\n{in2} 0.7 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)
            original_raw = [l.raw_text for l in doc.lines]
            assert len(doc) == 2
            assert not doc.can_undo
            assert not doc.can_redo

            # --- Mutation 1: delete line 1 ---
            doc.remove_line(doc[1].line_id)
            assert len(doc) == 1
            assert doc[0].data.net == "in1"
            assert doc.can_undo

            # --- Mutation 2: insert blank at position 0 ---
            blank = DocumentLine(
                raw_text="",
                validation_result=ValidationResult(status=LineStatus.OK),
            )
            doc.insert_line(0, blank)
            assert len(doc) == 2
            assert doc[0].raw_text == ""

            # --- Mutation 3: edit (replace) line at position 1 ---
            old_line = doc[1]
            ctrl.start_session(old_line.line_id)
            ctrl.set_net("in1")
            ctrl.set_af_value(0.99)
            ctrl.set_em_mode(True)
            ctrl.set_sh_mode(True)
            vr = ctrl.validate()
            committed_data = ctrl.to_line_data()
            raw = af_serializer.serialize(committed_data)
            new_line = DocumentLine(
                line_id=old_line.line_id,
                raw_text=raw,
                data=committed_data,
                validation_result=vr,
            )
            doc.replace_line(old_line.line_id, new_line)
            assert doc[1].data.af_value == 0.99

            # --- Undo 1: undo the replace → af_value back to 0.5 ---
            record = doc.undo()
            assert record is not None
            assert record.kind == "replace"
            assert doc[1].data.af_value == 0.5
            assert doc.can_redo

            # --- Undo 2: undo the insert → back to 1 line ---
            record = doc.undo()
            assert record is not None
            assert record.kind == "remove"  # undoing an insert = remove
            assert len(doc) == 1

            # --- Undo 3: undo the delete → back to 2 original lines ---
            record = doc.undo()
            assert record is not None
            assert record.kind == "insert"  # undoing a remove = insert
            assert len(doc) == 2
            restored_raw = [l.raw_text for l in doc.lines]
            assert restored_raw == original_raw

            # Nothing left to undo
            assert not doc.can_undo
            assert doc.undo() is None

            # --- Redo 1: redo the delete → 1 line ---
            record = doc.redo()
            assert record is not None
            assert record.kind == "remove"
            assert len(doc) == 1

            # --- Redo 2: redo the insert → 2 lines ---
            record = doc.redo()
            assert record is not None
            assert record.kind == "insert"
            assert len(doc) == 2
            assert doc[0].raw_text == ""

            # --- Redo 3: redo the replace → af_value back to 0.99 ---
            record = doc.redo()
            assert record is not None
            assert record.kind == "replace"
            assert doc[1].data.af_value == 0.99

            # Nothing left to redo
            assert not doc.can_redo
            assert doc.redo() is None
        finally:
            os.unlink(path)

    def test_new_mutation_clears_redo_stack(self, nqs):
        """After undoing, a new mutation should clear the redo stack."""
        content = "{in1} 0.5 net-regular_em_sh\n{in2} 0.7 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)

            doc.remove_line(doc[1].line_id)
            doc.undo()
            assert doc.can_redo

            # New mutation clears redo
            blank = DocumentLine(
                raw_text="",
                validation_result=ValidationResult(status=LineStatus.OK),
            )
            doc.insert_line(0, blank)
            assert not doc.can_redo
            assert doc.redo() is None
        finally:
            os.unlink(path)

    def test_swap_is_undoable(self, nqs):
        """Swapping two lines and undoing should restore original order."""
        content = "{in1} 0.5 net-regular_em_sh\n{in2} 0.7 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)
            raw0 = doc[0].raw_text
            raw1 = doc[1].raw_text

            doc.swap_lines(0, 1)
            assert doc[0].raw_text == raw1
            assert doc[1].raw_text == raw0

            doc.undo()
            assert doc[0].raw_text == raw0
            assert doc[1].raw_text == raw1
        finally:
            os.unlink(path)


# ======================================================================
# Step 6: Save & Reload
# ======================================================================

class TestStep6SaveAndReload:

    def test_save_and_reload_preserves_edits(self, nqs, ctrl):
        """
        Load a document, make edits (change af_value, comment a line),
        save, reload, and verify persisted state.
        """
        content = (
            "# header comment\n"
            "{in1} 0.5 net-regular_em_sh\n"
            "{in2} 0.7 net-regular_em_sh\n"
        )
        path = _write_tmp(content)
        save_path = _write_tmp("", suffix=".af.dcfg")
        try:
            doc = load_document(path, DocumentType.AF, nqs)

            # Edit line 1: change af to 0.99
            old_line = doc[1]
            ctrl.start_session(old_line.line_id)
            ctrl.set_net("in1")
            ctrl.set_af_value(0.99)
            ctrl.set_em_mode(True)
            ctrl.set_sh_mode(True)
            vr = ctrl.validate()
            committed = ctrl.to_line_data()
            raw = af_serializer.serialize(committed)
            new_line = DocumentLine(
                line_id=old_line.line_id,
                raw_text=raw,
                data=committed,
                validation_result=vr,
            )
            doc.replace_line(old_line.line_id, new_line)

            # Comment out line 2
            old_line2 = doc[2]
            commented = DocumentLine(
                line_id=old_line2.line_id,
                raw_text="# " + old_line2.raw_text,
                validation_result=ValidationResult(status=LineStatus.COMMENT),
            )
            doc.replace_line(old_line2.line_id, commented)

            # Save
            save_document(doc, save_path)

            # Reload
            doc2 = load_document(save_path, DocumentType.AF, nqs)
            assert len(doc2) == 3

            # Line 0: header comment preserved
            assert doc2[0].status == LineStatus.COMMENT
            assert "header comment" in doc2[0].raw_text

            # Line 1: edited af_value persisted
            assert doc2[1].data is not None
            assert doc2[1].data.af_value == 0.99
            assert doc2[1].data.net == "in1"

            # Line 2: commented out
            assert doc2[2].status == LineStatus.COMMENT
            assert doc2[2].raw_text.startswith("# ")
        finally:
            os.unlink(path)
            if os.path.exists(save_path):
                os.unlink(save_path)

    def test_save_after_undo_reflects_post_undo_state(self, nqs, ctrl):
        """
        Make two edits, undo one, save, reload. The reloaded document
        should reflect the post-undo state.
        """
        content = "{in1} 0.5 net-regular_em_sh\n{in2} 0.7 net-regular_em_sh\n"
        path = _write_tmp(content)
        save_path = _write_tmp("", suffix=".af.dcfg")
        try:
            doc = load_document(path, DocumentType.AF, nqs)

            # Edit line 0: af → 0.99
            old0 = doc[0]
            ctrl.start_session(old0.line_id)
            ctrl.set_net("in1")
            ctrl.set_af_value(0.99)
            ctrl.set_em_mode(True)
            ctrl.set_sh_mode(True)
            vr = ctrl.validate()
            d0 = ctrl.to_line_data()
            doc.replace_line(old0.line_id, DocumentLine(
                line_id=old0.line_id,
                raw_text=af_serializer.serialize(d0),
                data=d0, validation_result=vr,
            ))

            # Edit line 1: af → 0.11
            old1 = doc[1]
            ctrl.start_session(old1.line_id)
            ctrl.set_net("in2")
            ctrl.set_af_value(0.11)
            ctrl.set_em_mode(True)
            ctrl.set_sh_mode(True)
            vr1 = ctrl.validate()
            d1 = ctrl.to_line_data()
            doc.replace_line(old1.line_id, DocumentLine(
                line_id=old1.line_id,
                raw_text=af_serializer.serialize(d1),
                data=d1, validation_result=vr1,
            ))

            # Undo the second edit → line 1 back to af=0.7
            doc.undo()
            assert doc[1].data.af_value == 0.7

            # Save
            save_document(doc, save_path)

            # Reload and verify
            doc2 = load_document(save_path, DocumentType.AF, nqs)
            assert doc2[0].data.af_value == 0.99   # first edit kept
            assert doc2[1].data.af_value == 0.7     # second edit undone
        finally:
            os.unlink(path)
            if os.path.exists(save_path):
                os.unlink(save_path)

    def test_save_preserves_comments_and_empty_lines(self, nqs):
        """Comments and empty lines survive a save → reload cycle."""
        content = (
            "# first comment\n"
            "\n"
            "{in1} 0.5 net-regular_em_sh\n"
            "# trailing comment\n"
        )
        path = _write_tmp(content)
        save_path = _write_tmp("", suffix=".af.dcfg")
        try:
            doc = load_document(path, DocumentType.AF, nqs)
            save_document(doc, save_path)

            doc2 = load_document(save_path, DocumentType.AF, nqs)
            assert len(doc2) == 4
            assert doc2[0].status == LineStatus.COMMENT
            assert doc2[0].raw_text == "# first comment"
            assert doc2[1].raw_text == ""
            assert doc2[2].data is not None
            assert doc2[3].status == LineStatus.COMMENT
        finally:
            os.unlink(path)
            if os.path.exists(save_path):
                os.unlink(save_path)


# ======================================================================
# Additional integration edge cases
# ======================================================================

class TestConflictDetectionIntegration:
    """
    Focused tests for conflict detection at the core layer.
    """

    def test_cross_template_conflict_via_instance_names(self, nqs, detector):
        """
        {in1} (top-level) and {tpl:n1} (sub-template) both resolve to
        the same top-level instance name 'in1'.  They should conflict.
        """
        content = (
            "{in1} 0.5 net-regular_em_sh\n"
            "{tpl:n1} 1.0 net-regular_template-regular_em_sh\n"
        )
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)
            detector.rebuild(list(doc.lines))
            assert detector.is_conflicting(doc[0].line_id)
            assert detector.is_conflicting(doc[1].line_id)
        finally:
            os.unlink(path)

    def test_delete_one_conflicting_line_clears_conflict(self, nqs, detector):
        """
        Deleting one of two conflicting lines clears the conflict
        on the remaining line.
        """
        content = "{in1} 0.5 net-regular_em_sh\n{in1} 0.7 net-regular_em_sh\n"
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)
            detector.rebuild(list(doc.lines))
            assert detector.is_conflicting(doc[0].line_id)

            line1_id = doc[1].line_id
            doc.remove_line(line1_id)
            detector.remove_line(line1_id)
            assert not detector.is_conflicting(doc[0].line_id)
        finally:
            os.unlink(path)

    def test_three_way_conflict(self, nqs, detector):
        """
        Three lines all targeting in1: all three should be mutually
        conflicting, and removing one still leaves the other two
        in conflict.
        """
        content = (
            "{in1} 0.1 net-regular_em_sh\n"
            "{in1} 0.2 net-regular_em_sh\n"
            "{in1} 0.3 net-regular_em_sh\n"
        )
        path = _write_tmp(content)
        try:
            doc = load_document(path, DocumentType.AF, nqs)
            detector.rebuild(list(doc.lines))

            for i in range(3):
                assert detector.is_conflicting(doc[i].line_id)

            # Remove the middle line — the other two still conflict
            mid_id = doc[1].line_id
            doc.remove_line(mid_id)
            detector.remove_line(mid_id)
            assert detector.is_conflicting(doc[0].line_id)
            assert detector.is_conflicting(doc[1].line_id)  # was position 2
        finally:
            os.unlink(path)


class TestEditSessionValidation:
    """
    Test the AF edit session/controller validation across both
    Layer 2 (domain) and Layer 3 (netlist).
    """

    def test_session_validates_empty_net(self, nqs, ctrl):
        ctrl.start_session("sess-1")
        ctrl.set_net("")
        ctrl.set_af_value(0.5)
        ctrl.set_em_mode(True)
        ctrl.set_sh_mode(True)
        vr = ctrl.validate()
        assert not vr.is_valid
        assert any("net" in e.lower() for e in vr.errors)

    def test_session_validates_af_out_of_range(self, nqs, ctrl):
        ctrl.start_session("sess-2")
        ctrl.set_net("in1")
        ctrl.set_af_value(-0.5)
        ctrl.set_em_mode(True)
        ctrl.set_sh_mode(True)
        vr = ctrl.validate()
        assert not vr.is_valid
        assert any("af" in e.lower() for e in vr.errors)

    def test_session_validates_no_em_or_sh(self, nqs, ctrl):
        ctrl.start_session("sess-3")
        ctrl.set_net("in1")
        ctrl.set_af_value(0.5)
        ctrl.set_em_mode(False)
        ctrl.set_sh_mode(False)
        vr = ctrl.validate()
        assert not vr.is_valid
        assert any("em" in e.lower() or "sh" in e.lower() for e in vr.errors)

    def test_session_warns_on_unknown_net(self, nqs, ctrl):
        """A net not in the netlist should produce a warning, not an error."""
        ctrl.start_session("sess-4")
        ctrl.set_net("nonexistent_net")
        ctrl.set_af_value(0.5)
        ctrl.set_em_mode(True)
        ctrl.set_sh_mode(True)
        vr = ctrl.validate()
        assert vr.is_valid  # no errors
        assert vr.status == LineStatus.WARNING
        assert len(vr.warnings) >= 1

    def test_session_from_line_data_round_trip(self, nqs, ctrl):
        """Loading data into a controller and reading it back should preserve all fields."""
        from doc_types.af.line_data import AfLineData

        original = AfLineData(
            template="tpl",
            net="n1",
            af_value=0.42,
            is_template_regex=False,
            is_net_regex=False,
            is_em_enabled=True,
            is_sh_enabled=False,
        )
        ctrl.start_session("round-trip")
        ctrl.from_line_data(original)
        result = ctrl.to_line_data()

        assert result.template == original.template
        assert result.net == original.net
        assert result.af_value == original.af_value
        assert result.is_template_regex == original.is_template_regex
        assert result.is_net_regex == original.is_net_regex
        assert result.is_em_enabled == original.is_em_enabled
        assert result.is_sh_enabled == original.is_sh_enabled