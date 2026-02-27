from __future__ import annotations

import logging
from typing import Optional

from doc_types.mutex.exceptions import EntryNotFoundError

logger = logging.getLogger(__name__)
from doc_types.mutex.line_data import MutexLineData, FEVMode
from doc_types.mutex.entry import MutexEntry
from core.validation_result import ValidationResult

from doc_types.mutex.session import MutexEditSessionState
from core.interfaces import INetlistQueryService
from doc_types.mutex.validator import validate


class MutexEditController:

    def __init__(self, netlist_query_service: INetlistQueryService):
        self._nqs = netlist_query_service
        self._session = MutexEditSessionState("")

    # ---------------------------
    # Session lifecycle
    # ---------------------------

    def start_session(self, session_id: str) -> None:
        logger.debug("Mutex session started: %s", session_id)
        self._session = MutexEditSessionState(session_id)

    # ---------------------------
    # Properties (read-only views)
    # ---------------------------

    @property
    def session(self) -> MutexEditSessionState:
        return self._session

    # ---------------------------
    # Configuration (user actions)
    # ---------------------------
    def set_fev_mode(self, fev: FEVMode) -> None:
        self._session.fev = fev

    def set_num_active(self, value: int) -> None:
        self._session.num_active = value


    # ---------------------------
    # Mutation (user actions)
    # ---------------------------

    def add_mutexed(self, template: Optional[str], net_pattern: str, is_regex: bool = False) -> None:
        """
        Resolve a net pattern via the netlist service, build a MutexEntry,
        and add it to the session's mutexed set.
        Domain exceptions propagate to the caller.
        """
        net_pattern = self._nqs.normalize_net_for_template(net_pattern, template)
        matches = self._resolve(template, net_pattern, is_regex)
        entry = MutexEntry(
            net_name=net_pattern,
            template_name=template,
            regex_mode=is_regex,
            matches=matches,
        )
        self._session.add_mutexed(entry)

    def add_active(self, template: Optional[str], net_name: str) -> None:
        """
        Add an exact net to both mutexed and active sets.
        """
        net_name = self._nqs.normalize_net_for_template(net_name, template)
        matches = self._resolve(template, net_name, is_regex=False)
        entry = MutexEntry(
            net_name=net_name,
            template_name=template,
            regex_mode=False,
            matches=matches,
        )
        self._session.add_active(entry)

    def remove_mutexed(self, template: Optional[str], net_pattern: str, is_regex: bool = False) -> None:
        """
        Find and remove an entry from the mutexed set.
        """
        net_pattern = self._nqs.normalize_net_for_template(net_pattern, template)
        entry = self._find_mutexed(template, net_pattern, is_regex)
        self._session.remove_mutexed(entry)

    def remove_active(self, template: Optional[str], net_name: str) -> None:
        """
        Find and remove an entry from the active set.
        """
        net_name = self._nqs.normalize_net_for_template(net_name, template)
        entry = self._find_active(template, net_name)
        self._session.remove_active(entry)

    # ---------------------------
    # Lifecycle (interface)
    # ---------------------------

    def validate(self) -> ValidationResult:
        """
        Two-step validation, run in sequence:

        1. Session structural checks (enough nets, num_active bounds).
           If errors exist, return immediately — no point running NQS checks.
        2. NQS-aware checks via ``validate`` (bus expansion mismatches,
           missing nets, non-canonical names, template existence, …).

        Callers only see a single ValidationResult.  Errors mean "do not
        commit"; warnings mean "committed but worth surfacing".
        """
        session_result = self._session.validate()
        if not session_result:
            logger.debug("Mutex session validation failed: %s", session_result.errors)
            return session_result

        result = validate(self.to_line_data(), nqs=self._nqs)
        if result.warnings:
            logger.debug("Mutex validation warnings: %s", result.warnings)
        return result

    def to_line_data(self) -> MutexLineData:
        """
        Serialize current session state into a typed line data object.
        """
        return MutexLineData(
            num_active=self._session.num_active,
            fev=self._session.fev,
            is_net_regex=self._session.regex_mode,
            template=self._session.template,
            mutexed_nets=tuple(e.net_name for e in self._session.mutexed_entries),
            active_nets=tuple(e.net_name for e in self._session.active_entries),
        )

    def from_line_data(self, data: MutexLineData) -> None:
        """
        Hydrate session state from an existing line (edit flow).
        Rebuilds entries by resolving patterns against the current netlist.
        Template and regex_mode are derived from entries, not set directly.

        Uses session.loading() context to allow "invalid" entries (those that resolve to no nets)
        to be added without raising exceptions.
        These will surface as warning/errors during validate() instead of blocking the load.
        """
        self._session.fev = data.fev

        template = data.template or ""
        with self._session.loading():
            for net_name in data.mutexed_nets:
                if net_name in data.active_nets:
                    self.add_active(template, net_name)
                else:
                    self.add_mutexed(template, net_name, data.is_net_regex)

        # num_active is derived when active entries exist;
        # only set the explicit count when there are none.
        if not self._session.active_entries:
            self._session.num_active = data.num_active

    # ---------------------------
    # Private (resolution)
    # ---------------------------

    def _resolve(self, template: Optional[str], pattern: str, is_regex: bool) -> frozenset[str]:
        """
        Use NetlistQueryService to resolve a pattern into concrete net names.

        Always returns bare net names (no template prefix) so that
        matches are comparable regardless of how they were resolved.
        """
        if is_regex:
            nets, _ = self._nqs.find_matches(template, pattern, False, True)
            return frozenset(
                self._nqs.normalize_net_for_template(n, template) for n in nets
            )

        if self._nqs.has_bus_notation(pattern):
            expanded = self._nqs.expand_bus_notation(pattern)
            existing = [n for n in expanded if self._nqs.net_exists(n, template)]
            return frozenset(existing)

        canonical = self._nqs.get_canonical_net_name(pattern, template)
        return frozenset([canonical] if canonical else frozenset())

    def _find_mutexed(self, template: Optional[str], net_pattern: str, is_regex: bool) -> MutexEntry:
        """
        Find a MutexEntry in the mutexed set by template, net_pattern, and regex_mode.
        """
        for entry in self._session.mutexed_entries:
            if (
                entry.template_name == template
                and entry.net_name == net_pattern
                and entry.regex_mode == is_regex
            ):
                return entry
        raise EntryNotFoundError(
            f"No mutexed entry found for template='{template}', "
            f"net_pattern='{net_pattern}', is_regex={is_regex}."
        )

    def _find_active(self, template: Optional[str], net_name: str) -> MutexEntry:
        """
        Find a MutexEntry in the active set by template and net_name.
        """
        for entry in self._session.active_entries:
            if entry.template_name == template and entry.net_name == net_name:
                return entry
        raise EntryNotFoundError(
            f"No active entry found for template='{template}', net_name='{net_name}'."
        )
