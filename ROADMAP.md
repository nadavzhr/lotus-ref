# Lotus-Ref Roadmap

Items discovered during code review, prioritised by impact. Checked items
have already been implemented.

---

## Completed (Code Review Fixes)

- [x] **C3** — Move `DocumentService` from `app/` to `src/services/` so it
      is importable by any frontend, not just the FastAPI demo.
- [x] **H1** — Freeze `AfLineData` / `MutexLineData` (`frozen=True`) to
      prevent accidental mutation after commit.
- [x] **H2** — Atomic file writes via `tempfile` + `os.replace` in
      `document_io._write_text`.
- [x] **H3** — Fix file-handle leak in `NetlistBuilder` on parse failure.
- [x] **H4** — Make `ConflictInfo.conflicting_line_ids` a `frozenset` to
      guarantee immutability.
- [x] **L1** — Convert `IEditController` / `IEditSessionState` from ABC to
      `typing.Protocol` (structural subtyping, no inheritance required).
- [x] **M1** — Cap `_resolve_tpl_net_to_top_names` LRU cache at 4 096
      entries (was unbounded).
- [x] **M2** — Fix silent `None` coercion in mutex parser `is_regexp`
      detection.
- [x] **M4** — Add `logging.getLogger(__name__)` and targeted log
      statements to `document.py`, `conflict_store.py`, `document_io.py`,
      `af/controller.py`, `mutex/controller.py`, and `document_service.py`.
- [x] **L4** — Add explanatory comment to `_is_gz` suffix check.
- [x] **Search / filter lines** — `DocumentService.search_lines()` with
      substring, regex, and status-filter support; exposed via
      `GET /api/documents/{doc_id}/search`.
- [x] **Close / unload document** — `DocumentService.close_document()`;
      exposed via `DELETE /api/documents/{doc_id}`.

---

## Short-Term (Next Sprint)

### Undo / Redo with Command Pattern
Every mutation (edit, insert, delete) should be wrapped in a reversible
`Command` object held in a per-document undo stack.  This is the highest
priority missing feature — users currently have no way to revert an
accidental edit short of reloading from disk.

**Suggested design:**
```
class Command(Protocol):
    def execute(self) -> None: ...
    def undo(self) -> None: ...

class EditLineCommand:
    def __init__(self, doc, line_id, old_line, new_line): ...
```

### Pydantic Models for `from_dict` Boundary Validation  *(M3)*
`AfLineData` and `MutexLineData` are currently built via `dataclasses.asdict`
round-trips.  Type coercion and constraint checking only happen inside
the controller / session.  Add thin Pydantic models at the JSON → domain
boundary (`from_dict` in each handler) to get early, standardised
validation with clear error messages.

### Dry-Run Validation Endpoint
Add `POST /api/documents/{doc_id}/lines/{position}/validate` that runs the
full two-layer validation pipeline without committing, returning the
`ValidationResult` as JSON.  Enables a "Check" button in the UI.

---

## Medium-Term

### File Browser / Directory Listing Endpoint
Expose `GET /api/files?root=<path>` that returns the directory tree under
a given root, filtered to relevant extensions (`.dcfg`, `.dcfg.gz`,
`.sp`).  The frontend can use this to let users pick files to load
instead of typing paths manually.

### Diff / Preview Before Save
Before writing to disk, compute a unified diff (Python `difflib`) between
the file on disk and the in-memory document.  Expose it via
`GET /api/documents/{doc_id}/diff` so the frontend can show a side-by-side
or inline diff view before the user confirms the save.

### Problems Panel for Conflict Exploration
Group all lines with `status == conflict` into a dedicated view.  For each
conflict cluster, show the shared net names and link back to the
conflicting lines.  This mirrors the VS Code "Problems" panel UX.

---

## Long-Term / Nice-to-Have

### Mutex Parser: Regex → Manual Parser  *(M2 full)*
The current mutex parser is regex-based and handles edge cases via
progressively more complex patterns.  Converting to a hand-written
recursive-descent or PEG parser (like the AF parser) would improve
maintainability and make future syntax extensions straightforward.

### WebSocket / SSE for Live Updates
Replace polling with push-based updates so the frontend reacts
immediately to backend state changes (e.g., after a long validation or
background reload).

### Plugin Architecture for New Document Types
Formalise the `DocumentTypeHandler` registry into a plugin system so that
new config formats (e.g., timing constraints, power intent) can be added
as self-contained packages without touching core code.
