# TODO — Post Code Review

Actionable items from the code review, grouped by theme.
All 12 items have been implemented and verified. **308 tests passing.**

---

## 1. Immutability Enforcement

### 1.1 ~~Make `DocumentLine` frozen~~ ✅

**Problem:** `DocumentLine` is `@dataclass(slots=True)` but not `frozen=True`.
Fields (`data`, `validation_result`) are never mutated after construction — the
codebase always creates a new `DocumentLine` and calls `Document.replace_line`.
But nothing prevents accidental mutation.

**Design:** Change to `@dataclass(frozen=True, slots=True)`.  All existing call
sites already construct new instances — no code changes needed beyond the
decorator.

**Files:**
- `src/core/document_line.py` — add `frozen=True`
- Run full test suite to confirm nothing assigns to fields post-init.

---

### 1.2 ~~Make `MutexLineData` fields immutable~~ ✅

**Problem:** `mutexed_nets: list[str]` and `active_nets: list[str]` are mutable
lists.  The codebase only reads them (iteration, `len`, `in` checks) — never
appends, extends, or index-assigns.  But the type allows it.

**Design:** Change both fields to `tuple[str, ...]` with
`field(default_factory=tuple)`.  Update the parser and serializer constructors
to pass tuples.  `from_dict` should convert incoming lists to tuples.

**Files:**
- `src/doc_types/mutex/line_data.py` — change types + defaults
- `src/doc_types/mutex/parser.py` — wrap list comprehensions in `tuple(...)`
- `src/doc_types/mutex/serializer.py` — `from_dict` wraps with `tuple()`
- `src/doc_types/mutex/controller.py` — `to_line_data` builds tuples
- Tests that construct `MutexLineData` directly

---

### 1.3 ~~Make `ValidationResult` status-safe~~ ✅

**Problem:** `ValidationResult.__post_init__` silently overrides an explicitly
passed `status` if `errors` or `warnings` are also provided.  For example,
`ValidationResult(status=LineStatus.COMMENT, errors=["x"])` becomes `ERROR`.
This is correct for the normal parse flow but is a footgun for future callers.

**Design:** Remove `status` as a constructor parameter for the normal
data-line case.  Instead:

- For non-data lines (COMMENT, empty), provide a class method or keep the
  existing pattern: `ValidationResult(status=LineStatus.COMMENT)` works fine
  when `errors` and `warnings` are empty (post_init leaves it alone).
- Add a guard in `__post_init__`: if `status` was explicitly passed as
  something other than `OK` **and** `errors`/`warnings` are also present,
  raise a `ValueError`.  This prevents the silent-override case while
  keeping the ergonomic constructor for non-data lines.

**Files:**
- `src/core/validation_result.py` — add guard in `__post_init__`
- Tests to cover the guard

---

## 2. Error Handling & Logging

### 2.1 ~~Surface NQS regex errors to the UI~~ ✅

**Problem:** `NetlistQueryService._match_nets_regex` catches regex compilation
errors silently and returns `[]`.  A user entering an invalid regex pattern
sees "no matches" instead of an error message.

**Design:** Let `re.error` propagate from `NetlistDatabase.match_regex` up
through `_match_nets_regex` / `_get_matching_nets` / `find_matches`.  The
controller's `validate()` already runs `find_matches` — if it raises, the
API layer's `except Exception as e: raise HTTPException(422, str(e))` will
surface the regex syntax error to the UI.

Concretely:
- In `NetlistDatabase.match_regex`: let `re.error` propagate (the SQLite
  REGEXP function already returns 0 for invalid regex, but the Python-side
  wrapper should not silently eat it).
- In `_match_nets_regex`: remove the bare `except Exception` → replace with
  a targeted catch that re-raises `re.error` with a user-friendly message
  like `"Invalid regex pattern '<pattern>': <error>"`.
- Same for `_get_matching_templates` when `template_regex=True`.

**Files:**
- `src/nqs/netlist_query_service.py` — `_match_nets_regex`,
  `_get_matching_templates`
- `src/nqs/netlist_database.py` — review REGEXP function error handling

---

### 2.2 ~~Standardize logging across the codebase~~ ✅

**Problem:** `NetlistQueryService` defines a custom `get_logger()` that adds
handlers at the module level — an anti-pattern.  Logging config should happen at
the application entry point.

**Design:**
- Replace `get_logger(name)` with `logging.getLogger(__name__)` everywhere.
- Remove all handler/formatter setup from library modules.
- Optionally add a `logging.basicConfig(...)` call in `app/main.py` for the
  application entry point (or use `uvicorn`'s built-in config).
- NQS, infrastructure, and core modules should only call
  `logger.debug/info/warning/error` — never configure handlers.

**Files:**
- `src/nqs/netlist_query_service.py` — remove `get_logger`, use stdlib pattern
- `app/main.py` — optionally add `logging.basicConfig(level=logging.INFO)`

---

## 3. Simplify ConflictDetector — Eliminate Integer ID Table

### 3.1 ~~Remove `_net_id_map` / `_id_net_map`, use canonical net name strings directly~~ ✅

**Problem:** `ConflictDetector._build_id_table()` eagerly loads **all** top-cell
nets via `nqs.get_all_nets_in_template(top_cell)` at init time, assigns each a
sequential integer, and maintains bidirectional `name↔int` maps.  This is
premature optimization — typical config files have tens to hundreds of lines,
and `frozenset[str]` vs `frozenset[int]` is negligible at this scale.

The integer layer adds complexity:
- Two dicts to maintain (`_net_id_map`, `_id_net_map`)
- `canonical_net_name()` reverse-lookup for UI display
- Risk of stale IDs if the netlist ever changes (even though it's static today)

**Design:** Replace `frozenset[int]` with `frozenset[str]` throughout
`ConflictStore` and `ConflictDetector`.  Specifically:

1. **`ConflictStore`**: Change `_line_nets: dict[str, frozenset[str]]` and
   `_net_lines: dict[str, set[str]]`.  All method signatures change `int` →
   `str` for net IDs.  `ConflictInfo.shared_net_ids` → `frozenset[str]`
   (these are now human-readable net names directly).

2. **`ConflictDetector`**: Remove `_build_id_table`, `_net_id_map`,
   `_id_net_map`, and `canonical_net_name()`.  `_resolve_tpl_net_to_top_ids`
   returns `frozenset[str]` of top-cell canonical net names instead of ints.
   `resolve_to_canonical_names` returns `frozenset[str]`.

3. **`DocumentService._serialize_line`**: The conflict info already contains
   human-readable net names — remove the `canonical_net_name()` lookup loop.
   `shared_nets = sorted(info.shared_net_ids)` directly.

4. **Tests**: Update `ConflictStore` tests that use integer net IDs → use
   string net names instead.  The test logic stays the same.

This eliminates the upfront `get_all_nets_in_template` call and removes an
entire indirection layer with no performance regression for real workloads.

**Files:**
- `src/core/conflict_store.py` — full refactor of both classes
- `app/document_service.py` — simplify `_serialize_line` conflict section
- `tests/core/test_conflict_store.py` — update to use string IDs

---

## 4. Incremental Document Index Rebuild

### 4.1 ~~Avoid full `_rebuild_index()` on insert/remove~~ ✅

**Problem:** `Document.insert_line` and `remove_line` call `_rebuild_index()`
which rebuilds the entire `{line_id: position}` dict in O(n).  For documents
with thousands of lines, this is wasteful when only positions after the
mutation point change.

**Design:** Replace the full rebuild with incremental adjustment:

- **`insert_line(position, line)`**: Add the new line's entry, then increment
  `_index[line_id]` by 1 for all lines at positions `>= position + 1`.
- **`remove_line(line_id)`**: Note the position, delete the entry, then
  decrement `_index[line_id]` by 1 for all lines at positions `> old_pos`.

This is still O(n) in the worst case (insert at position 0) but avoids
re-hashing every key.  For the common case (append, remove near end) it's
nearly O(1).

Alternatively, if simplicity is preferred: keep the full rebuild but document
it as intentional.  The performance difference only matters for very large
files.

**Implementation note:** The `_lines_cache = None` invalidation stays as-is.
The `replace_line` method already handles same-ID replacement without a
rebuild — that path is unaffected.

**Files:**
- `src/core/document.py` — rewrite `insert_line`, `remove_line`
- `tests/core/test_document.py` — existing tests should still pass

---

## 5. Type Annotation Consistency

### 5.1 ~~Standardize on `from __future__ import annotations` everywhere~~ ✅

**Problem:** Some modules use `TYPE_CHECKING` guards for forward references,
others use `from __future__ import annotations`, some use both.  This
inconsistency makes it unclear which pattern new code should follow.

**Design:** Use `from __future__ import annotations` as the standard.  It
makes all annotations strings at runtime, eliminating the need for
`TYPE_CHECKING` guards in most cases.  Keep `TYPE_CHECKING` only when an
import is needed exclusively for type checkers (e.g., avoiding circular
imports at runtime) — but put `from __future__ import annotations` at the
top of every module regardless.

Files that need `from __future__ import annotations` added:
- `src/core/interfaces.py`
- `src/core/validation_result.py`
- `src/core/errors.py`
- `src/core/document_type.py`
- `src/core/line_status.py`
- `src/doc_types/af/controller.py`
- `src/doc_types/af/session.py`
- `src/doc_types/af/parser.py`
- `src/doc_types/af/validator.py`
- `src/doc_types/mutex/controller.py`
- `src/doc_types/mutex/session.py`
- `src/doc_types/mutex/entry.py`
- `src/doc_types/mutex/exceptions.py`
- `src/doc_types/mutex/parser.py`
- `src/doc_types/mutex/validator.py`
- `src/doc_types/mutex/serializer.py`
- `src/doc_types/af/serializer.py`
- `src/infrastructure/registrations.py`
- `src/nqs/netlist_query_service.py`

Remove redundant `TYPE_CHECKING` guards where `from __future__ import
annotations` already makes the forward reference a string.  Keep
`TYPE_CHECKING` only for imports that exist solely for type checkers AND
would cause a circular import at runtime.

---

### 5.2 ~~Define a `HasNetSpecs` protocol for `DocumentLine.data`~~ ✅

**Problem:** `DocumentLine.data` is typed as `LineData = object` at runtime
and `Union[AfLineData, MutexLineData]` under `TYPE_CHECKING`.  This is
correct for duck typing but unhelpful for tooling and debugging.

**Design:** Define a `Protocol` in `core/`:

```python
# core/interfaces.py (or core/protocols.py)
class HasNetSpecs(Protocol):
    def net_specs(self) -> list[NetSpec]: ...
```

Type `DocumentLine.data` as `HasNetSpecs | None`.  Both `AfLineData` and
`MutexLineData` already satisfy this protocol implicitly — no changes needed
on those classes.  `ConflictDetector.resolve_line_nets` can then type its
`data` parameter as `HasNetSpecs` instead of untyped `Any`.

**Files:**
- `src/core/interfaces.py` — add `HasNetSpecs` protocol
- `src/core/document_line.py` — change `data` type annotation
- `src/core/conflict_store.py` — type `resolve_line_nets(data)` parameter

---

## 6. `collapse_bus_notation` Cleanup

### 6.1 ~~Make `collapse_bus_notation` a `@staticmethod`~~ ✅

**Problem:** `NetlistQueryService.collapse_bus_notation` uses `self.BUS_PATTERN`
and `self.INDEX_PATTERN`, but both are class-level constants.  The method does
not access any instance state.

**Design:** Change to `@staticmethod` (or `@classmethod`).  Replace
`self.BUS_PATTERN` → `NetlistQueryService.BUS_PATTERN` (or
`cls.BUS_PATTERN` if using `@classmethod`).

**Files:**
- `src/nqs/netlist_query_service.py` — change decorator, update references

---

## 7. Test Coverage

### 7.1 ~~`DocumentService` integration tests~~ ✅

**Problem:** `DocumentService` is the most integration-critical class —
it wires session hydration, commit, conflict update propagation, and
serialization.  It has zero dedicated tests.

**Design:** Create `tests/test_document_service.py` using `MockNetlistQueryService`.
Test cases should cover:

- Load a document → verify summary, line count, status counts
- `hydrate_session` with `fields=None` → verify it loads existing data
- `hydrate_session` with fields dict → verify it applies new values
- `commit_edit` → verify the line is updated in the document, raw text is
  re-serialized, validation result is attached
- `commit_edit` → verify conflict detection is incrementally updated
- `get_lines` with pagination (`offset`, `limit`)
- `save` → verify file is written correctly
- Mutex flow: `hydrate_session` → `mutex_add_mutexed` → `mutex_add_active`
  → `commit_edit` → verify final line data
- Error cases: missing doc_id, invalid position, type mismatches

Use the existing `MockNetlistQueryService` from `tests/mock_nqs.py`.
Create fixture helper(s) for building pre-loaded `DocumentService` instances
with known documents.

**Files:**
- `tests/test_document_service.py` — new

---

### 7.2 ~~Property-based / fuzz testing on parsers~~ ✅

**Problem:** Parsers accept arbitrary user input.  The current test suite
covers known edge cases, but there may be uncovered crash paths or
unexpected behaviors for unusual (but valid-looking) inputs.

**Design:** Use `hypothesis` for property-based testing.  Key strategies:

- **Round-trip property:** For any `AfLineData` / `MutexLineData` generated
  by hypothesis, `parse(serialize(data))` should produce an equivalent
  `data` (after normalization).  This catches serializer/parser asymmetries.
- **No-crash property:** For any arbitrary string, `parse(text)` should
  either return a valid `LineData` or raise `ValueError` — never an
  unhandled exception.
- **Idempotent serialization:** `serialize(parse(serialize(data))) ==
  serialize(data)`.

Add `hypothesis` to `[project.optional-dependencies.dev]` in
`pyproject.toml`.

**Files:**
- `pyproject.toml` — add `hypothesis` to dev dependencies
- `tests/doc_types/af/test_parser_hypothesis.py` — new
- `tests/doc_types/mutex/test_parser_hypothesis.py` — new

---

## Execution Order

Dependencies dictate this sequence:

```
1.1  (DocumentLine frozen)               ← no deps, quick win
1.2  (MutexLineData tuples)              ← no deps, quick win
1.3  (ValidationResult guard)            ← no deps, quick win
2.1  (Surface regex errors)              ← no deps
2.2  (Standardize logging)               ← no deps
5.1  (Annotations consistency)           ← no deps, mechanical
5.2  (HasNetSpecs protocol)              ← after 5.1
6.1  (collapse_bus_notation static)      ← no deps, trivial
3.1  (Eliminate int ID table)            ← after 5.2 (uses new protocol)
4.1  (Incremental document index)        ← no deps
7.1  (DocumentService tests)             ← after 3.1 (tests new behavior)
7.2  (Hypothesis testing)                ← after 1.2 (tests new types)
```

Quick wins (single-file, low-risk):
**1.1, 1.2, 1.3, 2.2, 5.1, 6.1**

Largest impact:
**3.1** (simplifies ConflictDetector significantly),
**7.1** (closes the biggest test coverage gap)
