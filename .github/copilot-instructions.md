# Lotus-Ref Copilot Instructions

## Project Purpose
A DCFG (Design Configuration) document editor with netlist-aware validation. Edits two proprietary formats — **AF** (Activity Factor) and **Mutex** — where rules reference nets queried from a parsed SPICE netlist. Intended to become an Electron desktop app.

## Architecture

```
React/Zustand frontend → HTTP /api → FastAPI (app/) → DocumentService (services/)
                                                          ├── Document + undo/redo (core/)
                                                          ├── Registry dispatch (infrastructure/)
                                                          │     └── AF / Mutex handlers (doc_types/)
                                                          └── NetlistQueryService (nqs/) — SQLite in-memory
```

- **`src/core/interfaces.py`** defines `INetlistQueryService`, `IEditController[T]`, `IEditSessionState` as `Protocol`s — no inheritance, structural subtyping only.
- **`src/infrastructure/registrations.py`** is the sole wiring file for doc types; it calls `register()` for AF and Mutex. Adding a new doc type requires only a `register()` call here.
- **`src/services/document_service.py`** is the only facade routes should call. One controller instance is shared per `DocumentType` — only one edit session lives at a time.

## Developer Workflows

**Backend** (Python ≥ 3.12, `src/` layout):
```powershell
python -m uvicorn app.main:app --port 8000 --reload   # dev server
python -m pytest tests/                                # run all tests
```

**Frontend** (Vite + React + TypeScript):
```powershell
cd frontend
npx vite                  # dev server on :5173, proxies /api → localhost:8000
npx vite build            # outputs to app/static/ (served by FastAPI)
npx tsc --noEmit          # type-check only
```
Both servers must be running in dev. Production: build frontend first, then start uvicorn only.

## Core Conventions

### API ↔ Frontend boundary
- Frontend uses **0-based `position`** integers; the service converts them to stable `line_id` UUIDs immediately.
- All HTTP calls go through `frontend/src/api/documents.ts` → `api/client.ts`. Components **never** call `fetch` directly.
- TypeScript `DocumentLine` interface in `api/documents.ts` must mirror the backend JSON shape exactly.

### Edit session lifecycle (3-step)
1. `PUT /documents/{id}/lines/{pos}/session` with `fields: null` → `hydrate_session()` — loads existing line into controller.
2. Subsequent `PUT` with `fields: {...}` → updates session state without committing.
3. `POST /documents/{id}/lines/{pos}/commit` → `commit_edit()` — validates (structural, then NQS-aware), serializes, replaces line, updates conflict detector.

### Two-step validation
All controllers run structural validation first (no NQS), then NQS-aware validation. Short-circuits on structural errors so NQS is never queried for malformed lines.

### Conflict detection
`ConflictDetector.rebuild()` on load; `detector.update_line()` on every commit (incremental, not full rebuild). A line is conflicting if its resolved net instances overlap with any other line's nets.

### Registry / handler dispatch
`DocumentTypeHandler` in `registry.py` is a frozen dataclass of 7 callables: `is_comment`, `is_empty`, `parse`, `serialize`, `validate`, `from_dict`, `to_json`. Route handlers never call doc-type code directly — always via `get_handler(doc_type).method(...)`.

### Undo/redo
`Document` stores an undo stack of `Command` objects. Every mutation (`insert_line`, `remove_line`, `replace_line`, `swap_lines`) appends a command. The cached `lines` tuple is invalidated on every mutation.

## Test Patterns
- Integration tests live in `tests/integration/` and operate **directly on `Document`, controllers, and infra functions** — never through `DocumentService` (enforced by file-level docstring).
- `tests/mock_nqs.py` provides `MockNetlistQueryService` satisfying `INetlistQueryService` via explicit dicts (`canonical_map`, `net_matches`, `nets_in_template`) — no SPICE parsing.
- `tests/conftest.py` is empty; fixtures are defined per test file.

## Key Files
| File | Role |
|---|---|
| `src/core/interfaces.py` | All Protocols — start here to understand contracts |
| `src/infrastructure/registrations.py` | Doc-type wiring; only place to add new types |
| `src/services/document_service.py` | Application facade; all service logic lives here |
| `app/routes.py` | Full API surface (~25 endpoints) |
| `frontend/src/api/documents.ts` | All HTTP calls; TS types mirror backend JSON |
| `frontend/src/stores/document-store.ts` | Zustand store; mirrors the API surface |
| `src/nqs/netlist_query_service.py` | NQS impl with `@lru_cache` on `net_exists` |
