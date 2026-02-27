# Lotus-Ref Roadmap

Items discovered during code review, prioritised by impact. Checked items
have already been implemented.

---

## Short-Term (Next Sprint)



### Pydantic Models for `from_dict` Boundary Validation  *(M3)*
`AfLineData` and `MutexLineData` are currently built via `dataclasses.asdict`
round-trips.  Type coercion and constraint checking only happen inside
the controller / session.  Add thin Pydantic models at the JSON → domain
boundary (`from_dict` in each handler) to get early, standardised
validation with clear error messages.

---

## Medium-Term

### Problems Panel for Conflict Exploration
Group all lines with `status != ok | comment` into a dedicated view.
Sort by severity (error > warning > info) and allow clicking a line to explore
and see its details (e.g., for mutex conflicts, show the shared net names and the lines that match those nets).  This would be a major UX improvement for debugging complex documents with many conflicts, especially mutexes where the relationships are not immediately obvious from the line text alone.

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
