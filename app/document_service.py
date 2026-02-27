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
from typing import Any, Optional

from core import DocumentType, Document, DocumentLine, HasNetSpecs, LineStatus, IEditController, INetlistQueryService
from core.conflict_store import ConflictDetector
from core.validation_result import ValidationResult
from doc_types.af import AfEditController
from doc_types.mutex import FEVMode, MutexEditController
from infrastructure import load_document, save_document
from infrastructure.registry import get_handler



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
        doc = load_document(file_path, doc_type, self._nqs)
        self._documents[doc_id] = doc
        self._rebuild_conflicts(doc_id)
        return self._document_summary(doc_id, doc)

    def get_document(self, doc_id: str) -> Document:
        return self._documents[doc_id]

    def list_documents(self) -> list[dict]:
        return [
            self._document_summary(did, doc)
            for did, doc in self._documents.items()
        ]

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
        return self._document_summary(doc_id, doc)

    def insert_blank_line(self, doc_id: str, position: int) -> dict:
        """Insert an empty line at *position*. Returns ``{"position": int}``."""
        doc = self._documents[doc_id]
        new_line = DocumentLine(
            raw_text="",
            validation_result=ValidationResult(status=LineStatus.OK),
        )
        doc.insert_line(position, new_line)
        return {"position": position}

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, doc_id: str, file_path: Optional[str] = None) -> dict:
        """Write document back to disk."""
        doc = self._documents[doc_id]
        save_document(doc, file_path)
        return {"status": "saved", "file_path": file_path or doc.file_path}

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
        from collections import Counter
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

        # Conflict overlay — if the line is in conflict, override display status
        conflict_info = None
        if detector is not None:
            info = detector.get_conflict_info(line.line_id)
            if info is not None:
                status = LineStatus.CONFLICT.value
                # Net names are already human-readable strings
                shared_nets = sorted(info.shared_net_ids)
                # Translate internal line_ids to 0-based positions for the frontend
                conflicting_positions = sorted(
                    doc.get_position(lid)
                    for lid in info.conflicting_line_ids
                ) if doc is not None else []
                conflict_info = {
                    "conflicting_positions": conflicting_positions,
                    "shared_nets": shared_nets,
                }

        result = {
            "position": position,
            "raw_text": line.raw_text,
            "status": status,
            "errors": vr.errors,
            "warnings": vr.warnings,
            "has_data": line.data is not None,
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
