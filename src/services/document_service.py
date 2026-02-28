"""
DocumentService — the bridge between the API layer and the core domain.

Manages:
- Loaded documents (keyed by a doc_id string)
- A controller registry (one per DocumentType)
- Edit lifecycle: start_edit → update_session / mutate → commit_edit

The API layer addresses lines by 0-based position; the service resolves
positions to internal line_ids which are never exposed to the frontend.
"""
from __future__ import annotations

import dataclasses
import logging
import re
from collections import Counter
from typing import Any, Optional

from core import DocumentType, Document, DocumentLine, HasNetSpecs, LineStatus, IEditController, INetlistQueryService, MutationRecord
from core.conflict_store import ConflictDetector
from core.validation_result import ValidationResult
from doc_types.af import AfEditController
from doc_types.mutex import FEVMode, MutexEditController
from infrastructure import load_document, save_document, parse_line
from infrastructure.registry import get_handler

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Facade that the API layer calls. One instance per application.
    """

    def __init__(self, nqs: INetlistQueryService):
        self._nqs: INetlistQueryService = nqs
        self._documents: dict[str, Document] = {}
        self._conflict_detectors: dict[str, ConflictDetector] = {}
        self._controllers: dict[DocumentType, IEditController] = {
            DocumentType.AF: AfEditController(self._nqs),
            DocumentType.MUTEX: MutexEditController(self._nqs),
        }

    # ------------------------------------------------------------------
    # Document lifecycle
    # ------------------------------------------------------------------

    def load(self, doc_id: str, file_path: str, doc_type: DocumentType) -> dict:
        """Load a file into memory and return a summary."""
        logger.info("Loading document %s from %s (type=%s)", doc_id, file_path, doc_type.value)
        doc = load_document(file_path, doc_type, self._nqs)
        self._documents[doc_id] = doc
        self._rebuild_conflicts(doc_id)
        logger.info("Loaded document %s: %d lines", doc_id, len(doc))
        return self._document_summary(doc_id, doc)

    def get_document(self, doc_id: str) -> Document:
        return self._documents[doc_id]

    def list_documents(self) -> list[dict]:
        return [
            self._document_summary(did, doc)
            for did, doc in self._documents.items()
        ]

    def close_document(self, doc_id: str) -> None:
        """Remove a document from memory, freeing all associated resources."""
        self._documents.pop(doc_id, None)
        self._conflict_detectors.pop(doc_id, None)
        logger.info("Closed document %s", doc_id)

    # ------------------------------------------------------------------
    # Line access
    # ------------------------------------------------------------------

    def get_lines(
        self, doc_id: str, *, offset: int = 0, limit: Optional[int] = None,
    ) -> list[dict]:
        """Return lines in a document as JSON-friendly dicts.

        Args:
            offset: 0-based start position (default 0).
            limit:  Maximum number of lines to return.  ``None`` returns all.
        """
        doc = self._documents[doc_id]
        detector = self._conflict_detectors.get(doc_id)
        lines = doc.lines[offset : offset + limit if limit is not None else None]
        return [
            self._serialize_line(offset + i, line, detector, doc)
            for i, line in enumerate(lines)
        ]

    def get_line(self, doc_id: str, position: int) -> dict:
        doc = self._documents[doc_id]
        line = doc[position]
        detector = self._conflict_detectors.get(doc_id)
        return self._serialize_line(position, line, detector, doc)

    def search_lines(
        self,
        doc_id: str,
        query: str,
        *,
        use_regex: bool = False,
        status_filter: Optional[str] = None,
    ) -> list[dict]:
        """Search / filter lines in a document by content or status.

        Args:
            doc_id:        Loaded document identifier.
            query:         Substring (or regex if *use_regex*) to match in
                           ``raw_text``.  Empty string matches everything.
            use_regex:     Treat *query* as a regex pattern.
            status_filter: Optional status value to restrict results
                           (e.g. ``"error"``).

        Returns:
            List of serialized line dicts for matching lines.
        """
        doc = self._documents[doc_id]
        detector = self._conflict_detectors.get(doc_id)

        if use_regex:
            try:
                pattern = re.compile(query, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"Invalid regex: {exc}") from exc
        else:
            pattern = None

        results: list[dict] = []
        for pos, line in enumerate(doc.lines):
            # Text filter
            if query:
                if pattern is not None:
                    if not pattern.search(line.raw_text):
                        continue
                elif query.lower() not in line.raw_text.lower():
                    continue

            # Status filter
            if status_filter and line.status.value != status_filter:
                continue

            results.append(self._serialize_line(pos, line, detector, doc))
        return results

    # ------------------------------------------------------------------
    # Edit flow
    # ------------------------------------------------------------------

    def hydrate_session(
        self, doc_id: str, position: int, fields: Optional[dict] = None,
    ) -> dict:
        """
        Start or update an edit session for a line.

        If *fields* is ``None`` the session is hydrated from the line's
        existing data (user clicked "Edit").  Otherwise the incoming
        dict is converted to typed LineData and loaded into the
        controller (UI "Apply" for AF, or any field-based update).

        Does **not** commit — call :meth:`commit_edit` for that.
        """
        doc = self._documents[doc_id]
        line = doc[position]
        ctrl = self._controllers[doc.doc_type]

        ctrl.start_session(line.line_id)

        if fields is not None:
            line_data = self._dict_to_line_data(doc.doc_type, fields)
            ctrl.from_line_data(line_data)
        elif line.data is not None:
            ctrl.from_line_data(line.data)

        handler = get_handler(doc.doc_type)
        current_data = ctrl.to_line_data()
        logger.debug("Hydrated session for doc=%s pos=%d", doc_id, position)
        return {
            "position": position,
            "doc_type": doc.doc_type.value,
            "data": handler.to_json(current_data),
        }

    def commit_edit(self, doc_id: str, position: int) -> dict:
        """
        Commit the current edit session to the document.

        Type-agnostic — validates the controller state, serializes to
        raw text, replaces the line, and updates conflict detection.
        """
        doc = self._documents[doc_id]
        line_id = doc[position].line_id
        ctrl = self._controllers[doc.doc_type]

        # Validate via the controller (includes NQS warnings)
        vr = ctrl.validate()

        # Get the serialised data back from the controller
        committed_data = ctrl.to_line_data()

        # Serialize to raw text via the registry handler
        handler = get_handler(doc.doc_type)
        raw = handler.serialize(committed_data)

        new_line = DocumentLine(
            line_id=line_id,
            raw_text=raw,
            data=committed_data,
            validation_result=vr,
        )
        doc.replace_line(line_id, new_line)

        # Incremental conflict update — only recompute for this line
        detector = self._conflict_detectors.get(doc_id)
        if detector is not None:
            detector.update_line(line_id, committed_data)

        logger.info(
            "Committed edit doc=%s pos=%d status=%s",
            doc_id, position, vr.status.value,
        )
        return self._serialize_line(position, new_line, detector, doc)

    # ------------------------------------------------------------------
    # Line insertion / deletion
    # ------------------------------------------------------------------

    def delete_line(self, doc_id: str, position: int) -> dict:
        """Delete a line by its 0-based position. Returns the updated summary."""
        doc = self._documents[doc_id]
        line = doc[position]

        # Remove from conflict detection first
        detector = self._conflict_detectors.get(doc_id)
        if detector is not None:
            detector.remove_line(line.line_id)

        doc.remove_line(line.line_id)
        logger.info("Deleted line at pos=%d from doc=%s", position, doc_id)
        return self._document_summary(doc_id, doc)

    def insert_blank_line(self, doc_id: str, position: int) -> dict:
        """Insert an empty line at *position*. Returns ``{"position": int}``."""
        doc = self._documents[doc_id]
        new_line = DocumentLine(
            raw_text="",
            validation_result=ValidationResult(status=LineStatus.OK),
        )
        doc.insert_line(position, new_line)
        logger.debug("Inserted blank line at pos=%d in doc=%s", position, doc_id)
        return {"position": position}

    # ------------------------------------------------------------------
    # Swap lines
    # ------------------------------------------------------------------

    def swap_lines(self, doc_id: str, pos_a: int, pos_b: int) -> dict:
        """Swap two lines by position. Returns an updated document summary.

        Swaps change no net content so the conflict detector is unaffected —
        conflicting *positions* are resolved lazily via ``doc.get_position()``
        at serialization time.
        """
        doc = self._documents[doc_id]
        doc.swap_lines(pos_a, pos_b)
        logger.info("Swapped lines %d <-> %d in doc=%s", pos_a, pos_b, doc_id)
        return self._document_summary(doc_id, doc)

    # ------------------------------------------------------------------
    # Toggle comment
    # ------------------------------------------------------------------

    _COMMENT_PREFIX = "# "

    def toggle_comment(self, doc_id: str, position: int) -> dict:
        """Toggle the comment state of a line.

        - **Commenting** prepends ``# `` and marks the line as COMMENT.
        - **Uncommenting** strips the leading ``#`` (and one optional
          space) then re-parses the text via ``parse_line`` — this may
          produce OK, WARNING, or ERROR depending on validity.

        The operation is recorded for undo/redo via ``replace_line``.

        Returns the serialized replacement line.
        """
        doc = self._documents[doc_id]
        old_line = doc[position]
        handler = get_handler(doc.doc_type)

        if handler.is_comment(old_line.raw_text):
            # Uncomment — strip the comment indicator and re-parse
            stripped = old_line.raw_text.lstrip()
            # Remove leading '#' and optional single space
            if stripped.startswith("# "):
                raw = stripped[2:]
            elif stripped.startswith("#"):
                raw = stripped[1:]
            else:
                raw = stripped

            # Preserve leading whitespace from original line
            leading_ws = old_line.raw_text[: len(old_line.raw_text) - len(old_line.raw_text.lstrip())]
            raw = leading_ws + raw

            new_line = parse_line(raw, doc.doc_type, self._nqs)
            # Preserve the line_id so the undo replace works correctly
            new_line = DocumentLine(
                line_id=old_line.line_id,
                raw_text=new_line.raw_text,
                data=new_line.data,
                validation_result=new_line.validation_result,
            )
        else:
            # Comment — prepend '# ' to the raw text
            new_raw = self._COMMENT_PREFIX + old_line.raw_text
            new_line = DocumentLine(
                line_id=old_line.line_id,
                raw_text=new_raw,
                validation_result=ValidationResult(status=LineStatus.COMMENT),
            )

        doc.replace_line(old_line.line_id, new_line)

        # Incremental conflict update
        detector = self._conflict_detectors.get(doc_id)
        if detector is not None:
            if new_line.data is not None:
                detector.update_line(new_line.line_id, new_line.data)
            else:
                detector.remove_line(new_line.line_id)

        action = "uncommented" if handler.is_comment(old_line.raw_text) else "commented"
        logger.info("%s line at pos=%d in doc=%s", action.title(), position, doc_id)
        return self._serialize_line(position, new_line, detector, doc)

    def edit_comment_text(self, doc_id: str, position: int, new_text: str) -> dict:
        """Edit the raw text of a comment line.

        The line must currently be a comment. The *new_text* is stored
        as-is (it should already include the ``# `` prefix).  If the
        caller sends text without a leading ``#``, we prepend ``# ``.

        The operation is recorded for undo/redo via ``replace_line``.
        """
        doc = self._documents[doc_id]
        old_line = doc[position]
        handler = get_handler(doc.doc_type)

        if not handler.is_comment(old_line.raw_text):
            raise ValueError("Line is not a comment — use the regular edit flow")

        # Ensure the text stays a comment
        raw = new_text
        if not raw.lstrip().startswith("#"):
            raw = self._COMMENT_PREFIX + raw

        new_line = DocumentLine(
            line_id=old_line.line_id,
            raw_text=raw,
            validation_result=ValidationResult(status=LineStatus.COMMENT),
        )
        doc.replace_line(old_line.line_id, new_line)

        logger.info("Edited comment text at pos=%d in doc=%s", position, doc_id)
        detector = self._conflict_detectors.get(doc_id)
        return self._serialize_line(position, new_line, detector, doc)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, doc_id: str, file_path: Optional[str] = None) -> dict:
        """Write document back to disk."""
        doc = self._documents[doc_id]
        save_document(doc, file_path)
        target = file_path or doc.file_path
        logger.info("Saved document %s to %s", doc_id, target)
        return {"status": "saved", "file_path": target}

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def undo(self, doc_id: str) -> dict:
        """Undo the most recent mutation in *doc_id*.

        Returns a dict with the undo result and current undo/redo state.
        Raises ``ValueError`` when nothing to undo.
        """
        doc = self._documents[doc_id]
        record = doc.undo()
        if record is None:
            raise ValueError("Nothing to undo")
        self._sync_conflicts_from_record(doc_id, record)
        logger.info("Undo %s in doc=%s at pos=%d", record.kind, doc_id, record.position)
        return self._mutation_response(doc_id, doc, record)

    def redo(self, doc_id: str) -> dict:
        """Redo the most recently undone mutation in *doc_id*.

        Returns a dict with the redo result and current undo/redo state.
        Raises ``ValueError`` when nothing to redo.
        """
        doc = self._documents[doc_id]
        record = doc.redo()
        if record is None:
            raise ValueError("Nothing to redo")
        self._sync_conflicts_from_record(doc_id, record)
        logger.info("Redo %s in doc=%s at pos=%d", record.kind, doc_id, record.position)
        return self._mutation_response(doc_id, doc, record)

    # ------------------------------------------------------------------
    # NQS Query Preview
    # ------------------------------------------------------------------

    def query_nets(self, template: Optional[str], net_pattern: str,
                   template_regex: bool, net_regex: bool) -> dict:
        """Query NQS for matching nets and templates."""
        nets, templates = self._nqs.find_matches(
            template, net_pattern, template_regex, net_regex
        )
        return {"nets": nets, "templates": templates}

    # ------------------------------------------------------------------
    # Mutex interactive session
    # ------------------------------------------------------------------

    def mutex_add_mutexed(self, doc_id: str,
                          template: Optional[str], net_pattern: str,
                          is_regex: bool) -> dict:
        ctrl = self._require_mutex_ctrl(doc_id)
        ctrl.add_mutexed(template, net_pattern, is_regex)
        return self._serialize_mutex_session(ctrl)

    def mutex_add_active(self, doc_id: str,
                         template: Optional[str], net_name: str) -> dict:
        ctrl = self._require_mutex_ctrl(doc_id)
        ctrl.add_active(template, net_name)
        return self._serialize_mutex_session(ctrl)

    def mutex_remove_mutexed(self, doc_id: str,
                             template: Optional[str], net_pattern: str,
                             is_regex: bool) -> dict:
        ctrl = self._require_mutex_ctrl(doc_id)
        ctrl.remove_mutexed(template, net_pattern, is_regex)
        return self._serialize_mutex_session(ctrl)

    def mutex_remove_active(self, doc_id: str,
                            template: Optional[str], net_name: str) -> dict:
        ctrl = self._require_mutex_ctrl(doc_id)
        ctrl.remove_active(template, net_name)
        return self._serialize_mutex_session(ctrl)

    def mutex_set_fev(self, doc_id: str, fev: str) -> dict:
        ctrl = self._require_mutex_ctrl(doc_id)
        ctrl.set_fev_mode(FEVMode(fev) if fev else FEVMode.EMPTY)
        return self._serialize_mutex_session(ctrl)

    def mutex_set_num_active(self, doc_id: str, value: int) -> dict:
        ctrl = self._require_mutex_ctrl(doc_id)
        ctrl.set_num_active(value)
        return self._serialize_mutex_session(ctrl)

    def get_mutex_session(self, doc_id: str) -> dict:
        ctrl = self._require_mutex_ctrl(doc_id)
        return self._serialize_mutex_session(ctrl)

    # commit_mutex_edit removed — use the unified commit_edit() instead

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _document_summary(self, doc_id: str, doc: Document) -> dict:
        detector = self._conflict_detectors.get(doc_id)
        statuses = Counter(line.status.value for line in doc.lines)
        if detector:
            conflict_count = sum(
                1 for line in doc.lines if detector.is_conflicting(line.line_id)
            )
            if conflict_count:
                statuses["conflict"] = conflict_count
        return {
            "doc_id": doc_id,
            "doc_type": doc.doc_type.value,
            "file_path": doc.file_path,
            "total_lines": len(doc),
            "status_counts": dict(statuses),
            "can_undo": doc.can_undo,
            "can_redo": doc.can_redo,
        }

    @staticmethod
    def _serialize_line(
        position: int,
        line: DocumentLine,
        detector: Optional[ConflictDetector] = None,
        doc: Optional[Document] = None,
    ) -> dict:
        vr = line.validation_result
        status = line.status.value

        # Conflict overlay — surfaced separately from primary validation status
        conflict_info = None
        is_conflict = False
        if detector is not None:
            info = detector.get_conflict_info(line.line_id)
            if info is not None:
                is_conflict = True
                # Build per-peer detail: each entry tells the UI which
                # nets are shared with a specific other line.
                peers: list[dict] = []
                for peer_lid, shared in info.peers.items():
                    peer_pos = doc.get_position(peer_lid) if doc is not None else -1
                    peers.append({
                        "position": peer_pos,
                        "shared_nets": sorted(shared),
                    })
                peers.sort(key=lambda p: p["position"])
                conflict_info = {"peers": peers}

        result = {
            "position": position,
            "raw_text": line.raw_text,
            "status": status,
            "errors": vr.errors,
            "warnings": vr.warnings,
            "has_data": line.data is not None,
            "is_conflict": is_conflict,
            "conflict_info": conflict_info,
        }
        if line.data is not None:
            handler = get_handler(doc.doc_type) if doc is not None else None
            if handler is not None:
                result["data"] = handler.to_json(line.data)
            else:
                result["data"] = dataclasses.asdict(line.data)
        return result

    @staticmethod
    def _dict_to_line_data(doc_type: DocumentType, fields: dict) -> HasNetSpecs:
        """Convert a raw JSON dict into the appropriate typed LineData."""
        handler = get_handler(doc_type)
        return handler.from_dict(fields)

    def _require_mutex_ctrl(self, doc_id: str) -> MutexEditController:
        doc = self._documents[doc_id]
        if doc.doc_type != DocumentType.MUTEX:
            raise ValueError(f"Document {doc_id} is not a MUTEX document")
        return self._controllers[DocumentType.MUTEX]

    def _rebuild_conflicts(self, doc_id: str) -> None:
        """Rebuild conflict state from scratch for all lines in a document."""
        doc = self._documents[doc_id]
        detector = self._conflict_detectors.get(doc_id)
        if detector is None:
            detector = ConflictDetector(self._nqs)
            self._conflict_detectors[doc_id] = detector
        detector.rebuild(doc.lines)

    def _sync_conflicts_from_record(
        self, doc_id: str, record: MutationRecord,
    ) -> None:
        """Update the conflict detector after an undo/redo mutation."""
        detector = self._conflict_detectors.get(doc_id)
        if detector is None:
            return
        if record.kind == "swap":
            pass  # Swap changes no net content; conflict state is unaffected.
        elif record.kind == "remove":
            detector.remove_line(record.line_id)
        else:  # insert or replace
            data = record.new_line.data if record.new_line else None
            detector.update_line(record.line_id, data)

    def _mutation_response(
        self, doc_id: str, doc: Document, record: MutationRecord,
    ) -> dict:
        """Build the JSON response for an undo/redo operation."""
        detector = self._conflict_detectors.get(doc_id)
        result: dict = {
            "action": record.kind,
            "position": record.position,
            "can_undo": doc.can_undo,
            "can_redo": doc.can_redo,
        }
        if record.kind == "swap":
            result["position2"] = record.position2
        elif record.kind != "remove":
            line = doc[record.position]
            result["line"] = self._serialize_line(
                record.position, line, detector, doc,
            )
        return result

    @staticmethod
    def _serialize_mutex_session(ctrl: MutexEditController) -> dict:
        s = ctrl.session
        return {
            "template": s.template,
            "regex_mode": s.regex_mode,
            "num_active": s.num_active,
            "fev": s.fev.value,
            "mutexed_entries": [
                {
                    "net_name": e.net_name,
                    "template_name": e.template_name,
                    "regex_mode": e.regex_mode,
                    "match_count": len(e.matches),
                }
                for e in sorted(s.mutexed_entries, key=lambda e: e.net_name)
            ],
            "active_entries": [
                {
                    "net_name": e.net_name,
                    "template_name": e.template_name,
                    "regex_mode": e.regex_mode,
                    "match_count": len(e.matches),
                }
                for e in sorted(s.active_entries, key=lambda e: e.net_name)
            ],
        }
