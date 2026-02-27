# Refactor Plan

Based on the code review and discussion. Items are grouped by theme and ordered
by dependency — later items may depend on earlier ones.

---

## Phase 1 — Registry-Driven Generic Dispatch (eliminates hardcoded doc-type checks)

### 1.1 Extend `DocumentTypeHandler` with missing capabilities

**Problem:** `DocumentService` contains three hardcoded dispatch points
(`commit_edit` serializer, `_dict_to_line_data`, `_serialize_line` FEV enum
hack) because the handler only bundles `parse / serialize / validate / is_comment /
is_empty`. Everything else falls through to `isinstance` or `if doc_type ==`.

**Plan:**

Add two new fields to `DocumentTypeHandler[T]`:

```python
@dataclass(frozen=True, slots=True)
class DocumentTypeHandler(Generic[T]):
    # existing
    is_comment: Callable[[str], bool]
    is_empty:   Callable[[str], bool]
    parse:      Callable[[str], T]
    serialize:  Callable[[T], str]
    validate:   Callable[[T, Optional[INetlistQueryService]], ValidationResult]
    # NEW
    from_dict:  Callable[[dict], T]         # replaces _dict_to_line_data
    to_json:    Callable[[T], dict]          # replaces dataclasses.asdict + FEV hack
```

**Files:**
- `src/infrastructure/registry.py` — add fields
- `src/infrastructure/registrations.py` — register the new callables
- `src/doc_types/af/` — add `from_dict()` + `to_json()` free functions (new file
  or added to existing serializer)
- `src/doc_types/mutex/` — same; `to_json` handles `FEVMode → str` conversion
- `app/document_service.py`:
  - `_dict_to_line_data` → delegates to `handler.from_dict(fields)`
  - `_serialize_line` → delegates to `handler.to_json(data)` (no `isinstance`)
  - `commit_edit` → delegates to `handler.serialize(data)` (already available,
    just use it instead of the `if/else`)

### 1.2 Generic conflict `resolve_line_nets` via a protocol method

**Problem:** `ConflictDetector.resolve_line_nets` uses `isinstance(data,
AfLineData)` / `isinstance(data, MutexLineData)` to dispatch resolution — not
scalable.

**Observation (from review discussion):**

Both doc types ultimately represent:
- A list of `(template_pattern, net_pattern, is_template_regex, is_net_regex)` tuples
- AF produces exactly **one** such tuple: `(data.template, data.net, data.is_template_regex, data.is_net_regex)`
- Mutex produces **N** tuples (one per mutexed net): `(data.template, net, False, data.is_regexp)` for each `net in data.mutexed_nets`

**Plan — add a `net_specs` protocol method to LineData types:**

Define a lightweight `NetSpec` NamedTuple (or dataclass) in `core/`:

```python
# core/net_spec.py (new)
@dataclass(frozen=True, slots=True)
class NetSpec:
    template: Optional[str]
    net: str
    is_template_regex: bool
    is_net_regex: bool
```

Add a `net_specs() -> list[NetSpec]` method to both `AfLineData` and
`MutexLineData`:

- `AfLineData.net_specs()` → returns `[NetSpec(template, net, is_template_regex, is_net_regex)]`
- `MutexLineData.net_specs()` → returns `[NetSpec(template, net, False, is_regexp) for net in mutexed_nets]`

Then `ConflictDetector.resolve_line_nets` becomes:

```python
def resolve_line_nets(self, data) -> frozenset[int]:
    all_ids: set[int] = set()
    for spec in data.net_specs():
        all_ids.update(self.resolve_to_canonical_ids(
            spec.template, spec.net,
            spec.is_template_regex, spec.is_net_regex,
        ))
    return frozenset(all_ids)
```

No `isinstance`, no imports of concrete types, fully generic. Adding a third
doc type only requires implementing `net_specs()` on its LineData.

Also add `net_specs` to `DocumentTypeHandler` or define a `Protocol` so the
detector can call it without knowing concrete types:

```python
class HasNetSpecs(Protocol):
    def net_specs(self) -> list[NetSpec]: ...
```

**Files:**
- `src/core/net_spec.py` — new, defines `NetSpec`
- `src/core/__init__.py` — re-export
- `src/doc_types/af/line_data.py` — add `net_specs()` method
- `src/doc_types/mutex/line_data.py` — add `net_specs()` method
- `src/core/conflict_store.py` — rewrite `resolve_line_nets` to use
  `data.net_specs()`, remove `isinstance` and local imports

---

## Phase 2 — Merge `start_edit` + `update_session` into a single `hydrate_session`

**Problem:** `start_edit` and `update_session` both call `ctrl.start_session()`
+ `ctrl.from_line_data()`. The only difference is the **source** of the data:

| Method           | Data source                   | Used when                                      |
|------------------|-------------------------------|-------------------------------------------------|
| `start_edit`     | Existing `line.data`          | User clicks "Edit" — load current line into UI  |
| `update_session` | Incoming `fields` dict from UI| AF "Apply" — UI gathers fields, sends them back |

Both:
1. Look up the document & line
2. Call `ctrl.start_session(line.line_id)`
3. Hydrate via `ctrl.from_line_data(some_line_data)`
4. Return `{ position, doc_type, data: asdict(ctrl.to_line_data()) }`

**Plan — collapse into one endpoint:**

```
PUT /api/documents/{doc_id}/lines/{position}/session
```

- If request body has `{ "fields": {...} }` → build `LineData` from dict, hydrate
- If request body has `{ "fields": null }` or **no** `fields` key → hydrate from
  existing `line.data`

This means:
- **Frontend "Edit" button** sends `PUT .../session` with `fields: null` → gets
  back the current data for editing (replaces `POST .../edit`)
- **Frontend AF "Apply"** sends `PUT .../session` with `fields: { ... }` → same
  endpoint, hydrates from UI fields (replaces current `PUT .../session` behavior)
- **Mutex interactive flow** still uses dedicated mutex endpoints for granular ops;
  `PUT .../session` can be used for initial hydration when clicking "Edit".

Service-side renames:
- `start_edit()` + `update_session()` → **`hydrate_session(doc_id, position, fields=None)`**
- `commit_edit()` stays as-is

Route-side:
- Remove `POST /lines/{position}/edit`
- Keep `PUT /lines/{position}/session`; adjust to call `hydrate_session`
- `EditRequest` model: `fields` becomes `Optional[dict] = None`

**Files:**
- `app/document_service.py` — merge into `hydrate_session`
- `app/routes.py` — remove `/edit`, update `/session`
- `app/static/index.html` — `startEdit()` calls `PUT .../session` with
  `{ fields: null }` instead of `POST .../edit`
- tests (if any) that reference `start_edit` or `update_session` by name

---

## Phase 3 — Clean up unused `position` param in mutex service methods

**Problem:** All `mutex_add_mutexed`, `mutex_add_active`, `mutex_remove_*`,
`mutex_set_fev`, `mutex_set_num_active`, `get_mutex_session` service methods
accept `position: int` but never use it. The routes DO send it (from the URL).

**Plan:**

Remove `position` from all mutex service method signatures. The route handler
still extracts it from the URL for RESTful consistency (the URL identifies the
resource), but does not forward it to the service — the service only needs
`doc_id` to find the controller.

Alternatively, reconsider whether these mutex endpoints even need `position`
in the URL. For now, keep it in the URL (it identifies the line being edited)
but drop it from the service layer.

**Files:**
- `app/document_service.py` — remove `position` param from
  `mutex_add_mutexed`, `mutex_add_active`, `mutex_remove_mutexed`,
  `mutex_remove_active`, `mutex_set_fev`, `mutex_set_num_active`,
  `get_mutex_session`
- `app/routes.py` — stop passing `position` to these service calls

---

## Phase 4 — Consolidate duplicated AF validation

**Problem:** `AFEditSessionState.validate()` reimplements the same three checks
as `af/validator.py`'s Layer 2 (AF value range, EM/SH, net name). If rules
change, both must be updated independently.

**Plan:**

`AFEditSessionState.validate()` should delegate to the shared validator:

```python
def validate(self) -> ValidationResult:
    return af_validate(self.to_line_data())  # Layer 2 only, no nqs
```

The controller's `validate()` already does:
```python
session_result = self._session.validate()   # → delegates to af_validate(data)
if not session_result:
    return session_result
return af_validate(self.to_line_data(), nqs=self._nqs)  # Layer 2 + 3
```

This is still fine — the session `validate()` runs Layer 2 cheaply; the
controller adds Layer 3. No duplication.

**Files:**
- `src/doc_types/af/session.py` — rewrite `validate()` to delegate

---

## Phase 5 — Maintainability Fixes

### 5.1 Naming consistency

| Current                      | Fix                          |
|------------------------------|------------------------------|
| `AFEditSessionState`         | → `AfEditSessionState`       |
| `is_regexp` (MutexLineData)  | → `is_net_regex`             |

The `is_regexp` rename is **wide-reaching**: parser, serializer, validator,
session, controller, test fixtures, frontend form field IDs. Needs a
methodical find-and-replace across all occurrences.

For AF, `is_template_regex` and `is_net_regex` are already correct.

**Files:**
- `src/doc_types/af/session.py` — rename class `AFEditSessionState` → `AfEditSessionState`
- `src/doc_types/af/__init__.py` — update export
- `src/doc_types/mutex/line_data.py` — rename `is_regexp` → `is_net_regex`
- All mutex files that reference `is_regexp` (parser, serializer, validator,
  session, controller, tests)
- `app/document_service.py` — `_dict_to_line_data` key, `_serialize_line`
- `app/static/index.html` — form field IDs
- all tests referencing these names

### 5.2 Remove wildcard import in `mutex/session.py`

Replace:
```python
from doc_types.mutex.exceptions import *
```
With explicit imports of actually-used exception classes.

**Files:**
- `src/doc_types/mutex/session.py`

### 5.3 Replace `sys.path` manipulation with proper packaging

Add a `pyproject.toml` with editable install so `src/` packages are
importable without runtime path hacks.

```toml
[project]
name = "lotus-ref"
version = "0.1.0"
requires-python = ">=3.12"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Then `pip install -e .` and remove `sys.path.insert()` from `conftest.py`
and `main.py`.

**Files:**
- `pyproject.toml` — new
- `tests/conftest.py` — remove sys.path hack
- `app/main.py` — remove sys.path hack
- `pytest.ini` — can be kept or migrated to `pyproject.toml`

---

## Phase 6 — Readability & Style

### 6.1 Extract `NetlistDatabase` from `NetlistQueryService`

Move all SQLite lifecycle and query methods into a dedicated class:

```python
class NetlistDatabase:
    """In-memory SQLite store for (template, net) pairs."""
    def __init__(self, data: dict[str, set[str]]) -> None: ...
    def match_regex(self, templates, pattern) -> list[tuple]: ...
    def match_exact(self, templates, name) -> list[tuple]: ...
    def match_bus(self, templates, expanded) -> list[tuple]: ...
    def close(self) -> None: ...
```

`NetlistQueryService` uses `self._db = NetlistDatabase(...)` internally.

Move the following methods from NQS → `NetlistDatabase`:
- `_init_database`
- `_execute_sql_query`
- `_cleanup_database`
- `_match_nets_regex`
- `_match_nets_exact`
- `_match_nets_bus`
- `close`, `__enter__`, `__exit__`, `__del__`
- `_db_lock`, `_is_closed`, `_db_conn` state

This drops NQS from ~708 → ~400 lines and gives the DB component a testable
boundary.

**Files:**
- `src/nqs/netlist_database.py` — new
- `src/nqs/netlist_query_service.py` — refactored to use `NetlistDatabase`

### 6.2 Add `__all__` to `conflict_store.py`

```python
__all__ = ["ConflictStore", "ConflictInfo", "ConflictDetector"]
```

**Files:**
- `src/core/conflict_store.py`

---

## Phase 7 — API Layer Design-for-Scale (low overhead)

### 7.1 Pagination on `get_lines`

Add optional `offset` / `limit` query params to `GET /documents/{doc_id}/lines`:

```python
@router.get("/documents/{doc_id}/lines")
def get_lines(doc_id: str, offset: int = 0, limit: int | None = None):
```

Default behavior (no params) returns all lines — backward compatible.
Service slices internally: `doc.lines[offset:offset+limit]`.

**Files:**
- `app/routes.py` — add params
- `app/document_service.py` — accept `offset`/`limit`, slice

### 7.2 Avoid copying `Document.lines` on every access

`Document.lines` currently returns `tuple(self._lines)` which copies the
entire list. Options:

- a) Return `typing.Sequence` view (e.g., `types.MappingProxyType` equivalent
  for lists — doesn't exist natively). Simplest: just iterate `_lines`
  directly where needed.
- b) Cache the tuple and invalidate on mutation.

Preferred: (b) — add `_lines_cache: tuple | None` which is set to `None` on
any mutation and built lazily on access. Minimal overhead.

**Files:**
- `src/core/document.py`

---

## Execution Order

Dependencies dictate this sequence:

```
Phase 1.2  (NetSpec + net_specs() on LineData)        ← no deps
Phase 1.1  (Extend handler, eliminate isinstance)     ← depends on 1.2 for to_json
Phase 4    (AF session validate delegation)           ← no deps
Phase 5.2  (Wildcard import)                          ← no deps
Phase 6.2  (__all__ in conflict_store)                ← no deps
Phase 2    (Merge start_edit + update_session)        ← after 1.1 (uses handler.from_dict)
Phase 3    (Remove unused position from mutex svc)    ← after Phase 2
Phase 5.1  (Naming: AFEdit→AfEdit, is_regexp→is_net_regex)  ← do last, widest blast radius
Phase 5.3  (pyproject.toml packaging)                 ← independent, can be anytime
Phase 6.1  (Extract NetlistDatabase)                  ← independent
Phase 7.1  (Pagination)                               ← after Phase 2
Phase 7.2  (Document.lines cache)                     ← independent
```

Quick wins that can be done immediately with no risk:
**Phase 4, 5.2, 6.2** — each is a single-file, low-risk change.

Largest blast radius: **Phase 5.1** (naming renames) — save for last.
