from __future__ import annotations

from doc_types.mutex.exceptions import (
    DuplicateEntryError,
    TemplateMismatchError,
    RegexModeMismatchError,
    IntersectionError,
    ActiveRegexError,
    ActiveMultipleMatchesError,
    NoMatchesError,
    EntryNotFoundError,
    InvalidFEVModeError,
)
from doc_types.mutex.entry import MutexEntry
from core.validation_result import ValidationResult
from doc_types.mutex.line_data import FEVMode

from contextlib import contextmanager

class MutexEditSessionState:

    def __init__(self, session_id: str):
        self.session_id = session_id

        self._mutexed: set[MutexEntry] = set()
        self._active: set[MutexEntry] = set()
        self._num_active: int = 1
        self._fev_mode: FEVMode = FEVMode.EMPTY

        self._loading: bool = False

    # ---------------------------
    # Derived session state
    # ---------------------------

    @property
    def template(self) -> str | None:
        if not self._mutexed:
            return None
        return next(iter(self._mutexed)).template_name

    @property
    def regex_mode(self) -> bool | None:
        if not self._mutexed:
            return None
        return next(iter(self._mutexed)).regex_mode

    @property
    def mutexed_entries(self) -> frozenset[MutexEntry]:
        return frozenset(self._mutexed)

    @property
    def active_entries(self) -> frozenset[MutexEntry]:
        return frozenset(self._active)

    # ---------------------------
    # Configuration properties with invariants
    # ---------------------------

    @contextmanager
    def loading(self):
        """
        Context manager that puts the session in 'loading' mode.
        During loading, entries with no matches are allowed (they will
        surface as warnings during validate() instead of blocking the load).
        Use this when hydrating session state from existing line data.
        """
        self._loading = True
        try:
            yield
        finally:
            self._loading = False
    
    @property
    def num_active(self) -> int:
        if self.active_entries:
            return len(self.active_entries)
        return self._num_active

    @num_active.setter
    def num_active(self, value: int):
        if self.active_entries:
            raise ValueError(
                "Cannot set num_active when there are already active entries. "
                "Clear active entries before setting num_active."
            )
        if value < 0:
            raise ValueError("num_active cannot be negative.")

        self._num_active = value

    @property
    def fev(self) -> FEVMode:
        return self._fev_mode

    @fev.setter
    def fev(self, value: FEVMode):
        if value not in FEVMode:
            raise InvalidFEVModeError(f"FEV mode must be one of {list(FEVMode)}, but got '{value}'.")
        self._fev_mode = value

    # ---------------------------
    # Mutation operations
    # ---------------------------

    def add_mutexed(self, entry: MutexEntry):
        if entry in self._mutexed:
            raise DuplicateEntryError(f"Entry {entry} is already in the mutexed set.")

        if self.template is not None and entry.template_name != self.template:
            raise TemplateMismatchError(
                f"Entry {entry} has template {entry.template_name} "
                f"which does not match session template {self.template}."
            )

        if not self._loading and not entry.matches:
            raise NoMatchesError(f"Entry {entry} must resolve to at least one net.")

        if (
            self.regex_mode is not None
            and entry.regex_mode != self.regex_mode
        ):
            raise RegexModeMismatchError(
                f"Entry {entry} has regex mode {entry.regex_mode} "
                f"which does not match session regex mode {self.regex_mode}."
            )

        for existing in self._mutexed:
            if entry.intersects(existing):
                raise IntersectionError(
                    f"Entry {entry} intersects with existing mutexed entry {existing}."
                )

        self._mutexed.add(entry)

    def add_active(self, entry: MutexEntry):
        if entry in self._active:
            raise DuplicateEntryError(f"Entry {entry} is already in the active set.")

        if entry.regex_mode:
            raise ActiveRegexError(
                f"Entry {entry} cannot be active because it is a regex entry."
            )
        if not entry.matches:
            raise NoMatchesError(
                f"Entry {entry} cannot be active because it does not resolve to any nets."
            )
        if len(entry.matches) != 1:
            raise ActiveMultipleMatchesError(
                f"Entry {entry} must resolve to exactly one net to be active, "
                f"but resolves to {len(entry.matches)} nets."
            )

        net = next(iter(entry.matches))
        if not any(net in entry.matches for entry in self._mutexed): 
            if self.regex_mode:
                raise EntryNotFoundError(
                    f"Net '{net}' is not covered by any mutexed pattern. "
                    f"Add a regex pattern that matches this net first."
                )
            self.add_mutexed(entry)
        self._active.add(entry)

    def remove_mutexed(self, entry: MutexEntry):
        if entry not in self._mutexed:
            raise EntryNotFoundError(f"Entry {entry} is not in the mutexed set.")

        for active_entry in list(self._active):
            if entry.intersects(active_entry):
                self._active.remove(active_entry)

        self._mutexed.remove(entry)

    def remove_active(self, entry: MutexEntry):
        if entry not in self._active:
            raise EntryNotFoundError(f"Entry {entry} is not in the active set.")

        self._active.remove(entry)

    def validate(self) -> ValidationResult:
        """
        Check whether the session is complete and ready to commit.
        Invariants (template consistency, regex mode, intersections, active validity)
        are enforced at mutation time and are not re-checked here.
        """
        errors = []

        mutexed_net_count = sum(len(entry.matches) for entry in self._mutexed)
        if mutexed_net_count < 2:
            errors.append(
                f"At least 2 unique nets must be mutexed, "
                f"but only {mutexed_net_count} unique nets are mutexed."
            )

        # num_active vs mutexed net count
        if mutexed_net_count > 0 and self.num_active >= mutexed_net_count:
            errors.append(
                f"Number of active nets ({self.num_active}) must be less than "
                f"number of unique mutexed nets ({mutexed_net_count})."
            )

        return ValidationResult(errors=errors)
