"""
ConflictStore — efficient conflict detection between document lines.

A conflict occurs when two or more lines resolve to overlapping sets
of canonical net IDs (integers).  The store maintains two indexes for
close-to-O(1) lookups:

- ``_line_nets[line_id]``  → frozenset of canonical net IDs
- ``_net_lines[net_id]``   → set of line_ids that cover that net

Canonical net IDs are integers assigned by the ConflictDetector at startup.
String names are stored once and resolved only for UI display, keeping the
core indexes compact and cache-friendly.

ConflictDetector owns both the ID mapping and the ConflictStore.  It
is fully rebuilt from all document lines on every edit to guarantee
consistency — a single line change can affect arbitrarily many other
lines, so incremental updates are not attempted.

Usage::

    detector = ConflictDetector(nqs)
    detector.rebuild(doc.lines)

    detector.is_conflicting("line-1")
    detector.get_conflict_info("line-1")
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.document_line import DocumentLine
    from core.interfaces import INetlistQueryService


class ConflictStore:
    """
    Maintains a bidirectional index of line ↔ canonical-net-ID
    relationships and exposes efficient conflict queries.
    """

    __slots__ = ("_line_nets", "_net_lines")

    def __init__(self) -> None:
        # line_id → frozenset of canonical net IDs (integers)
        self._line_nets: dict[str, frozenset[int]] = {}
        # canonical_net_id → set of line_ids
        self._net_lines: dict[int, set[str]] = {}

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def update_line(self, line_id: str, nets: set[int] | frozenset[int]) -> None:
        """
        Set (or replace) the canonical net IDs for *line_id*.

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

    def build_from_lines(self, line_nets: dict[str, frozenset[int]]) -> None:
        """
        Build both indexes from scratch in a single pass.

        Faster than repeated :meth:`update_line` calls during a full
        rebuild because it skips the per-line ``_remove_line_from_index``
        overhead — both indexes start empty.
        """
        self._line_nets = {lid: nets for lid, nets in line_nets.items() if nets}
        net_lines: dict[int, set[str]] = {}
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

    def get_conflicting_net_ids(self, line_id: str) -> frozenset[int]:
        """Return the canonical net IDs that *line_id* shares with at least one other line."""
        nets = self._line_nets.get(line_id)
        if not nets:
            return frozenset()
        result: set[int] = set()
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
        return ConflictInfo(conflicting_line_ids=lines, shared_net_ids=net_ids)

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
    conflicting_line_ids: set[str]
    shared_net_ids: frozenset[int]


# ------------------------------------------------------------------
# ConflictDetector — separate from the query service
# ------------------------------------------------------------------

class ConflictDetector:
    """
    Owns all conflict-detection logic and a :class:`ConflictStore`.

    It holds a reference to an :class:`INetlistQueryService` but never
    mutates it.  The service remains completely unaware of conflicts;
    it only answers queries.  The detector translates those query
    results into integer canonical-net-ID sets and maintains the
    bidirectional index via :class:`ConflictStore`.

    Conflict state is always rebuilt from scratch (via :meth:`rebuild`)
    because a single line change can cascade into conflicts with
    arbitrarily many other lines.

    Performance
    -----------
    * The (template, canonical_net) → top-cell-IDs mapping is resolved
      lazily with an unbounded cache.  Each unique pair is traversed
      through the hierarchy exactly once for the lifetime of the detector.
    * ``resolve_to_canonical_ids`` has a fast path for the common case
      (exact template, exact net, no regex/bus): pure in-memory lookups
      with no SQL involved.
    * Full rebuilds use :meth:`ConflictStore.build_from_lines` to
      construct both indexes in a single batch pass.
    """

    def __init__(self, nqs: "INetlistQueryService") -> None:
        self._nqs = nqs
        self._store = ConflictStore()
        self._top_cell = nqs.get_top_cell()
        self._build_id_table()

    # ------------------------------------------------------------------
    # ID table — maps top-cell canonical net names ↔ integers
    # ------------------------------------------------------------------

    def _build_id_table(self) -> None:
        top_nets = sorted(self._nqs.get_all_nets_in_template(self._top_cell))
        self._net_id_map: dict[str, int] = {
            name: i for i, name in enumerate(top_nets)
        }
        self._id_net_map: dict[int, str] = dict(enumerate(top_nets))

    def canonical_net_name(self, net_id: int) -> Optional[str]:
        """Return the human-readable net name for an integer ID."""
        return self._id_net_map.get(net_id)

    # ------------------------------------------------------------------
    # Hierarchy cache — resolved lazily, never evicted
    # ------------------------------------------------------------------

    @lru_cache(maxsize=None)
    def _resolve_tpl_net_to_top_ids(self, tpl: str, net: str) -> frozenset[int]:
        """
        Map a single (template, canonical_net) to top-cell integer IDs.

        Uses ``find_net_instance_names`` to walk the hierarchy, then
        maps the resulting top-cell names to integer IDs.  Cached with
        no size limit so each pair is resolved at most once.
        """
        names = self._nqs.find_net_instance_names(tpl, net)
        return frozenset(
            self._net_id_map[n] for n in names if n in self._net_id_map
        )

    # ------------------------------------------------------------------
    # Resolution — pattern → frozenset[int]
    # ------------------------------------------------------------------

    @lru_cache(maxsize=512)
    def resolve_to_canonical_ids(
        self,
        template: Optional[str],
        net_name: str,
        template_regex: bool,
        net_regex: bool,
    ) -> frozenset[int]:
        """
        Resolve a template/net pattern to top-cell canonical net IDs.

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

        result_ids: set[int] = set()

        if not net_regex and not nqs.has_bus_notation(net_norm):
            # ── Fast path: exact match — pure in-memory lookups ──
            for tpl in matching_templates:
                canonical = nqs.get_canonical_net_name(net_norm, tpl)
                if canonical:
                    result_ids.update(
                        self._resolve_tpl_net_to_top_ids(tpl, canonical)
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
                result_ids.update(
                    self._resolve_tpl_net_to_top_ids(tpl, net)
                )

        return frozenset(result_ids)

    # ------------------------------------------------------------------
    # Line resolution helpers
    # ------------------------------------------------------------------

    def resolve_line_nets(self, data) -> frozenset[int]:
        """
        Resolve the set of top-cell canonical net IDs that a line's
        data covers.

        *data* may be an :class:`AfLineData` or :class:`MutexLineData`.
        Returns a frozenset of integer canonical net IDs.
        """
        from doc_types.af.line_data import AfLineData
        from doc_types.mutex.line_data import MutexLineData

        if isinstance(data, AfLineData):
            return self.resolve_to_canonical_ids(
                data.template, data.net,
                data.is_template_regex, data.is_net_regex,
            )

        if isinstance(data, MutexLineData):
            all_ids: set[int] = set()
            for net in data.mutexed_nets:
                all_ids.update(
                    self.resolve_to_canonical_ids(
                        data.template, net,
                        False, data.is_regexp,
                    )
                )
            return frozenset(all_ids)

        return frozenset()

    # ------------------------------------------------------------------
    # Full rebuild
    # ------------------------------------------------------------------

    def rebuild(self, lines: list["DocumentLine"]) -> None:
        """
        Rebuild conflict state from scratch for all *lines*.

        This is the **only** mutation path — no incremental updates.
        A single line change can create or resolve conflicts with
        arbitrarily many other lines, so we always rebuild entirely.

        Uses :meth:`ConflictStore.build_from_lines` for a single-pass
        batch build (no per-line remove-from-index overhead).
        """
        line_nets: dict[str, frozenset[int]] = {}
        for line in lines:
            if line.data is not None:
                nets = self.resolve_line_nets(line.data)
                if nets:
                    line_nets[line.line_id] = nets
        self._store.build_from_lines(line_nets)

    # ------------------------------------------------------------------
    # Query delegation to store
    # ------------------------------------------------------------------

    def is_conflicting(self, line_id: str) -> bool:
        return self._store.is_conflicting(line_id)

    def get_conflicting_lines(self, line_id: str) -> set[str]:
        return self._store.get_conflicting_lines(line_id)

    def get_conflicting_net_ids(self, line_id: str) -> frozenset[int]:
        return self._store.get_conflicting_net_ids(line_id)

    def get_conflict_info(self, line_id: str) -> Optional[ConflictInfo]:
        return self._store.get_conflict_info(line_id)
