"""
Core interfaces (Protocols) for the document editing system.

This module defines the contracts that document types implement:
- INetlistQueryService: protocol for querying netlist data
- IEditController: orchestrates editing a single line
- IEditSessionState: mutable state for a single line edit session

All interfaces use ``typing.Protocol`` for structural (duck-typed) subtyping.
Concrete implementations do not need to inherit from these classes;
they only need to provide the required attributes and methods.
"""
from __future__ import annotations

from typing import Generic, Protocol, Optional, TypeVar, runtime_checkable

from core.net_spec import NetSpec
from core.validation_result import ValidationResult

T = TypeVar("T")


class HasNetSpecs(Protocol):
    """Any line-data object that can enumerate its net references."""
    def net_specs(self) -> list[NetSpec]: ...


class INetlistQueryService(Protocol):
    """
    Protocol defining the netlist query service interface.
    Controllers depend on this protocol, not the concrete implementation.
    """

    def find_matches(
        self,
        template_name: Optional[str],
        net_name: str,
        template_regex: bool,
        net_regex: bool,
    ) -> tuple[list[str], list[str]]: ...

    def find_net_instance_names(
        self,
        template: str,
        net_name: str,
    ) -> set[str]: ...

    def get_canonical_net_name(
        self,
        net_name: str,
        template_name: Optional[str] = None
    ) -> Optional[str]: ...

    def get_all_nets_in_template(
        self,
        template: Optional[str] = None,
    ) -> set[str]: ...

    def get_top_cell(self) -> str: ...

    def get_matching_templates(
        self,
        template_pattern: str,
        is_regex: bool
    ) -> set[str]: ...

    def template_exists(self,
        template_name: str
    ) -> bool: ...

    def net_exists(
        self,
        net_name: str,
        template_name: Optional[str] = None
    ) -> bool: ...

    @staticmethod
    def normalize_net_for_template(
        net_name: str,
        template_name: Optional[str]
    ) -> str: ...

    @staticmethod
    def has_bus_notation(
        net_name: str
    ) -> bool: ...

    @staticmethod
    def expand_bus_notation(
        pattern: str,
        max_expansions: Optional[int] = None
    ) -> list[str]: ...


@runtime_checkable
class IEditSessionState(Protocol):
    """Mutable state for a single line edit session."""
    session_id: str

    def validate(self) -> ValidationResult:
        """
        Check whether the session is complete and ready to commit.
        """
        ...


@runtime_checkable
class IEditController(Protocol[T]):
    """
    Orchestrates editing a single line in a document.

    One controller instance exists per document type.  It holds a
    long-lived reference to the netlist query service and always
    has a valid session.  Call ``start_session`` to begin editing
    a specific line (replaces any previous session).

    Lifecycle::

        ctrl = SomeEditController(nqs)
        ctrl.start_session("line-42")   # begin editing
        ctrl.set_...(...)               # user actions
        data = ctrl.to_line_data()       # commit
        ctrl.start_session("line-99")   # or move on to another line
    """

    def start_session(self, session_id: str) -> None:
        """Create a fresh session for the given line."""
        ...

    def validate(self) -> ValidationResult:
        """Validate session state + service-level checks (warnings)."""
        ...

    def to_line_data(self) -> T:
        """Serialize current session state into a typed line data object."""
        ...

    def from_line_data(self, data: T) -> None:
        """Hydrate session state from an existing line (edit flow)."""
        ...
