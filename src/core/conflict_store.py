"""
ConflictStore — efficient conflict detection between document lines.

A conflict occurs when two or more lines resolve to overlapping sets
of instance nets.  The store maintains two indexes for close-to-O(1)
lookups:

- ``_line_nets[line_id]``  → frozenset of nets the line covers
- ``_net_lines[net]``      → set of line_ids that cover that net

All mutations are incremental: updating or removing a single line
touches only the nets that line previously/newly covers, so no full
rebuild is needed for single-line edits.

Usage::

    store = ConflictStore()
    store.update_line("line-1", {"vdd", "vss"})
    store.update_line("line-2", {"vdd", "gnd"})

    store.is_conflicting("line-1")          # True
    store.get_conflicting_lines("line-1")   # {"line-2"}
    store.get_conflicting_nets("line-1")    # {"vdd"}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from doc_types.af.line_data import AfLineData
    from doc_types.mutex.line_data import MutexLineData
    from core.interfaces import INetlistQueryService


class ConflictStore:
    """
    Maintains a bidirectional index of line ↔ net relationships and
    exposes efficient conflict queries.
    """

    __slots__ = ("_line_nets", "_net_lines")

    def __init__(self) -> None:
        # line_id → frozenset of net names
        self._line_nets: dict[str, frozenset[str]] = {}
        # net_name → set of line_ids
        self._net_lines: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def update_line(self, line_id: str, nets: set[str] | frozenset[str]) -> None:
        """
        Set (or replace) the nets for *line_id*.

        If the line already existed, its old nets are first removed from
        the reverse index, then the new nets are inserted.  This is the
        main incremental-update entry point.
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

    def get_conflicting_nets(self, line_id: str) -> set[str]:
        """Return the nets that *line_id* shares with at least one other line."""
        nets = self._line_nets.get(line_id)
        if not nets:
            return set()
        result: set[str] = set()
        for net in nets:
            owners = self._net_lines.get(net)
            if owners and len(owners) > 1:
                result.add(net)
        return result

    def get_conflict_info(self, line_id: str) -> Optional["ConflictInfo"]:
        """
        Return a :class:`ConflictInfo` for *line_id*, or ``None`` if the
        line is not in conflict.
        """
        nets = self.get_conflicting_nets(line_id)
        if not nets:
            return None
        lines = self.get_conflicting_lines(line_id)
        return ConflictInfo(conflicting_line_ids=lines, shared_nets=nets)

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
    shared_nets: set[str]


# ------------------------------------------------------------------
# Net resolution helpers
# ------------------------------------------------------------------

def resolve_line_nets(
    data: "AfLineData | MutexLineData",
    nqs: "INetlistQueryService",
) -> frozenset[str]:
    """
    Resolve the set of canonical instance-net names that *data* covers,
    using the existing ``find_matches`` functionality on *nqs*.

    Returns a frozenset of fully qualified net names (e.g. ``"template:net"``
    or bare ``"net"`` for the top cell).
    """
    from doc_types.af.line_data import AfLineData
    from doc_types.mutex.line_data import MutexLineData

    if isinstance(data, AfLineData):
        nets, _ = nqs.find_matches(
            data.template, data.net,
            data.is_template_regex, data.is_net_regex,
        )
        return frozenset(nets)

    if isinstance(data, MutexLineData):
        all_nets: set[str] = set()
        for net in data.mutexed_nets:
            matched, _ = nqs.find_matches(
                data.template, net,
                False, data.is_regexp,
            )
            all_nets.update(matched)
        return frozenset(all_nets)

    return frozenset()
