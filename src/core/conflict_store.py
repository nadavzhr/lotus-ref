"""
ConflictStore — efficient conflict detection between document lines.

A conflict occurs when two or more lines resolve to overlapping sets
of canonical net names (strings).  The store maintains two indexes for
close-to-O(1) lookups:

- ``_line_nets[line_id]``  → frozenset of canonical net names
- ``_net_lines[net_name]`` → set of line_ids that cover that net

ConflictDetector owns a ConflictStore and an NQS reference.
It supports efficient incremental updates:

* **Edit line X** — resolve the new nets for X and call
  ``store.update_line(X, new_nets)``.  The store removes X from old
  net→lines entries and adds it to the new ones.  Conflict queries
  for *all* lines are immediately consistent because they read the
  bidirectional index at query time.
* **Insert new line X** — new lines are always empty, so no store
  update is needed.
* **Remove line X** — call ``store.remove_line(X)`` which cleans up
  both indexes.  No full scan required.

A full rebuild via :meth:`ConflictDetector.rebuild` is used only on
initial document load to populate the store in a single batch pass.

Usage::

    detector = ConflictDetector(nqs)
    detector.rebuild(doc.lines)               # initial load

    detector.update_line("line-1", line_data) # after edit
    detector.remove_line("line-1")            # after delete

    detector.is_conflicting("line-1")
    detector.get_conflict_info("line-1")
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.document_line import DocumentLine
    from core.interfaces import HasNetSpecs, INetlistQueryService

__all__ = ["ConflictStore", "ConflictInfo", "ConflictDetector"]


class ConflictStore:
    """
    Maintains a bidirectional index of line ↔ canonical net name
    relationships and exposes efficient conflict queries.
    """

    __slots__ = ("_line_nets", "_net_lines")

    def __init__(self) -> None:
        # line_id → frozenset of canonical net names (strings)
        self._line_nets: dict[str, frozenset[str]] = {}
        # canonical_net_name → set of line_ids
        self._net_lines: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def update_line(self, line_id: str, nets: set[str] | frozenset[str]) -> None:
        """
        Set (or replace) the canonical net names for *line_id*.

        If the line already existed, its old nets are first removed from
        the reverse index, then the new nets are inserted.
        """
        self._remove_line_from_index(line_id)

        new_nets = frozenset(nets)
        if not new_nets:
            # No nets — line doesn't participate in conflicts.
            self._line_nets.pop(line_id, None)
            return

        self._line_nets[line_id] = new_nets
        for net in new_nets:
            self._net_lines.setdefault(net, set()).add(line_id)

    def build_from_lines(self, line_nets: dict[str, frozenset[str]]) -> None:
        """
        Build both indexes from scratch in a single pass.

        Faster than repeated :meth:`update_line` calls during a full
        rebuild because it skips the per-line ``_remove_line_from_index``
        overhead — both indexes start empty.
        """
        self._line_nets = {lid: nets for lid, nets in line_nets.items() if nets}
        net_lines: dict[str, set[str]] = {}
        for line_id, nets in self._line_nets.items():
            for net in nets:
                net_lines.setdefault(net, set()).add(line_id)
        self._net_lines = net_lines

    def remove_line(self, line_id: str) -> None:
        """Remove a line and clean up both indexes."""
        self._remove_line_from_index(line_id)
        self._line_nets.pop(line_id, None)

    def clear(self) -> None:
        """Reset the entire store."""
        self._line_nets.clear()
        self._net_lines.clear()

    # ------------------------------------------------------------------
    # Queries (all close to O(1) for typical data)
    # ------------------------------------------------------------------

    def is_conflicting(self, line_id: str) -> bool:
        """Return True if *line_id* shares at least one net with another line."""
        nets = self._line_nets.get(line_id)
        if not nets:
            return False
        for net in nets:
            owners = self._net_lines.get(net)
            if owners and len(owners) > 1:
                return True
        return False

    def get_conflicting_lines(self, line_id: str) -> set[str]:
        """Return the set of other line_ids that share nets with *line_id*."""
        nets = self._line_nets.get(line_id)
        if not nets:
            return set()
        result: set[str] = set()
        for net in nets:
            owners = self._net_lines.get(net)
            if owners:
                result.update(owners)
        result.discard(line_id)
        return result

    def get_conflicting_net_ids(self, line_id: str) -> frozenset[str]:
        """Return the canonical net names that *line_id* shares with at least one other line."""
        nets = self._line_nets.get(line_id)
        if not nets:
            return frozenset()
        result: set[str] = set()
        for net in nets:
            owners = self._net_lines.get(net)
            if owners and len(owners) > 1:
                result.add(net)
        return frozenset(result)

    def get_conflict_info(self, line_id: str) -> Optional["ConflictInfo"]:
        """
        Return a :class:`ConflictInfo` for *line_id*, or ``None`` if the
        line is not in conflict.
        """
        net_ids = self.get_conflicting_net_ids(line_id)
        if not net_ids:
            return None
        lines = self.get_conflicting_lines(line_id)
        return ConflictInfo(conflicting_line_ids=frozenset(lines), shared_net_ids=net_ids)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _remove_line_from_index(self, line_id: str) -> None:
        """Remove *line_id* from the reverse net→lines index."""
        old_nets = self._line_nets.get(line_id)
        if not old_nets:
            return
        for net in old_nets:
            owners = self._net_lines.get(net)
            if owners:
                owners.discard(line_id)
                if not owners:
                    del self._net_lines[net]


@dataclass(frozen=True, slots=True)
class ConflictInfo:
    """Lightweight snapshot of conflict data for a single line."""
    conflicting_line_ids: frozenset[str]
    shared_net_ids: frozenset[str]


# ------------------------------------------------------------------
# ConflictDetector — separate from the query service
# ------------------------------------------------------------------

class ConflictDetector:
    """
    Owns all conflict-detection logic and a :class:`ConflictStore`.

    It holds a reference to an :class:`INetlistQueryService` but never
    mutates it.  The service remains completely unaware of conflicts;
    it only answers queries.  The detector translates query results into
    canonical net name sets and maintains the bidirectional index via
    :class:`ConflictStore`.

    Incremental updates
    -------------------
    Because the ConflictStore maintains a bidirectional index
    (line→nets and net→lines), a single ``store.update_line()`` call
    is sufficient to keep *all* conflict queries consistent:

    * Old net→lines entries for the edited line are removed.
    * New net→lines entries are added.
    * Queries like ``is_conflicting(any_line)`` read the live index
      and immediately reflect the change — no "update both sides" loop
      is needed.

    This means:

    * **Edit line X**: call ``update_line(line_id, data)`` — O(|nets_of_X|)
    * **Insert new line X**: no-op (new lines are always empty)
    * **Remove line X**: call ``remove_line(line_id)`` — O(|old_nets_of_X|)

    A full :meth:`rebuild` is used only on initial document load.

    Performance
    -----------
    * The (template, canonical_net) → top-cell names mapping is resolved
      lazily with an unbounded cache.  Each unique pair is traversed
      through the hierarchy exactly once for the lifetime of the detector.
    * ``resolve_to_canonical_names`` has a fast path for the common case
      (exact template, exact net, no regex/bus): pure in-memory lookups
      with no SQL involved.
    * Full rebuilds use :meth:`ConflictStore.build_from_lines` to
      construct both indexes in a single batch pass.
    """

    def __init__(self, nqs: "INetlistQueryService") -> None:
        self._nqs = nqs
        self._store = ConflictStore()
        self._top_cell = nqs.get_top_cell()

    # ------------------------------------------------------------------
    # Hierarchy cache — resolved lazily, never evicted
    # ------------------------------------------------------------------

    @lru_cache(maxsize=4096)
    def _resolve_tpl_net_to_top_names(self, tpl: str, net: str) -> frozenset[str]:
        """
        Map a single (template, canonical_net) to top-cell net names.

        Uses ``find_net_instance_names`` to walk the hierarchy, then
        returns the resulting top-cell names.  Cached with no size limit
        so each pair is resolved at most once.
        """
        return frozenset(self._nqs.find_net_instance_names(tpl, net))

    # ------------------------------------------------------------------
    # Resolution — pattern → frozenset[str]
    # ------------------------------------------------------------------

    @lru_cache(maxsize=512)
    def resolve_to_canonical_names(
        self,
        template: Optional[str],
        net_name: str,
        template_regex: bool,
        net_regex: bool,
    ) -> frozenset[str]:
        """
        Resolve a template/net pattern to top-cell canonical net names.

        Fast path (exact template + exact net, ~99 % of calls):
            1. In-memory set membership for template     — O(1)
            2. Cached canonical-name resolution           — O(1)
            3. Cached hierarchy lookup via pre-built map  — O(1)

        Slow path (regex / bus notation):
            Uses ``find_matches`` for pattern expansion, then maps
            each result through the hierarchy cache.
        """
        if not net_name:
            return frozenset()

        nqs = self._nqs
        tpl_name = (template or self._top_cell)
        tpl_name = tpl_name.lower() if not template_regex else tpl_name
        net_norm = net_name.lower() if not net_regex else net_name

        matching_templates = nqs.get_matching_templates(tpl_name, template_regex)
        if not matching_templates:
            return frozenset()

        result_names: set[str] = set()

        if not net_regex and not nqs.has_bus_notation(net_norm):
            # ── Fast path: exact match — pure in-memory lookups ──
            for tpl in matching_templates:
                canonical = nqs.get_canonical_net_name(net_norm, tpl)
                if canonical:
                    result_names.update(
                        self._resolve_tpl_net_to_top_names(tpl, canonical)
                    )
        else:
            # ── Slow path: regex / bus — delegate pattern expansion to NQS ──
            matching_nets, _ = nqs.find_matches(
                tpl_name, net_norm, template_regex, net_regex,
            )
            for qualified_net in matching_nets:
                if ":" in qualified_net:
                    tpl, net = qualified_net.split(":", 1)
                else:
                    tpl, net = self._top_cell, qualified_net
                result_names.update(
                    self._resolve_tpl_net_to_top_names(tpl, net)
                )

        return frozenset(result_names)

    # ------------------------------------------------------------------
    # Line resolution helpers
    # ------------------------------------------------------------------

    def resolve_line_nets(self, data: HasNetSpecs) -> frozenset[str]:
        """
        Resolve the set of top-cell canonical net names that a line's
        data covers.

        *data* must expose a ``net_specs()`` method returning a list of
        :class:`NetSpec` instances.  Returns a frozenset of canonical
        net name strings.
        """
        specs = getattr(data, "net_specs", None)
        if specs is None:
            return frozenset()

        all_names: set[str] = set()
        for spec in specs():
            all_names.update(
                self.resolve_to_canonical_names(
                    spec.template, spec.net,
                    spec.is_template_regex, spec.is_net_regex,
                )
            )
        return frozenset(all_names)

    # ------------------------------------------------------------------
    # Full rebuild (initial load only)
    # ------------------------------------------------------------------

    def rebuild(self, lines: list["DocumentLine"]) -> None:
        """
        Rebuild conflict state from scratch for all *lines*.

        Used **only** during initial document load.  After that, the
        incremental :meth:`update_line` and :meth:`remove_line` methods
        keep the index consistent without scanning all lines.

        Uses :meth:`ConflictStore.build_from_lines` for a single-pass
        batch build (no per-line remove-from-index overhead).
        """
        line_nets: dict[str, frozenset[str]] = {}
        for line in lines:
            if line.data is not None:
                nets = self.resolve_line_nets(line.data)
                if nets:
                    line_nets[line.line_id] = nets
        self._store.build_from_lines(line_nets)
        logger.debug(
            "Conflict index rebuilt: %d lines with nets, %d unique nets",
            len(line_nets),
            sum(len(nets) for nets in line_nets.values()),
        )

    # ------------------------------------------------------------------
    # Incremental updates
    # ------------------------------------------------------------------

    def update_line(self, line_id: str, data: HasNetSpecs | None) -> None:
        """
        Incrementally update conflict state after editing *line_id*.

        Resolves the new canonical net names from *data* and updates the
        store's bidirectional index.  Because conflict queries read the
        live index, all ``is_conflicting`` / ``get_conflict_info`` calls
        for **every** line immediately reflect the change.

        *data* is the line's parsed data (``AfLineData`` /
        ``MutexLineData``), or ``None`` for comment / blank lines.

        Complexity: O(|old_nets| + |new_nets|) — no full scan.
        """
        if data is None:
            self._store.remove_line(line_id)
        else:
            nets = self.resolve_line_nets(data)
            self._store.update_line(line_id, nets)

    def remove_line(self, line_id: str) -> None:
        """
        Remove *line_id* from the conflict index after deletion.

        Cleans up both sides of the bidirectional index so that other
        lines that previously conflicted with *line_id* are updated.

        Complexity: O(|nets_of_line|) — no full scan.
        """
        self._store.remove_line(line_id)

    # ------------------------------------------------------------------
    # Query delegation to store
    # ------------------------------------------------------------------

    def is_conflicting(self, line_id: str) -> bool:
        return self._store.is_conflicting(line_id)

    def get_conflicting_lines(self, line_id: str) -> set[str]:
        return self._store.get_conflicting_lines(line_id)

    def get_conflicting_net_ids(self, line_id: str) -> frozenset[str]:
        return self._store.get_conflicting_net_ids(line_id)

    def get_conflict_info(self, line_id: str) -> Optional[ConflictInfo]:
        return self._store.get_conflict_info(line_id)
