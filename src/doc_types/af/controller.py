from __future__ import annotations

from typing import Optional

from doc_types.af.line_data import AfLineData
from core.validation_result import ValidationResult
from doc_types.af.session import AfEditSessionState
from core.interfaces import IEditController, INetlistQueryService
from doc_types.af.validator import validate


class AfEditController(IEditController[AfLineData]):

    def __init__(self, netlist_query_service: INetlistQueryService):
        self._nqs = netlist_query_service
        self._session = AfEditSessionState("")  # Initialize with an empty session; will be replaced on start_session

    # ---------------------------
    # Session lifecycle
    # ---------------------------

    def start_session(self, session_id: str) -> None:
        self._session = AfEditSessionState(session_id)

    # ---------------------------
    # Properties (read-only views)
    # ---------------------------

    @property
    def session(self) -> AfEditSessionState:
        return self._session

    # ---------------------------
    # Mutation (user actions)
    # ---------------------------

    def set_template(self, name: Optional[str]) -> None:
        self._session.template_name = name

    def set_template_regex(self, is_regex: bool = True) -> None:
        self._session.template_regex_mode = is_regex

    def set_net(self, name: str) -> None:
        self._session.net_name = name
        
    def set_net_regex(self, is_regex: bool = True) -> None:
        self._session.net_regex_mode = is_regex

    def set_af_value(self, value: float) -> None:
        self._session.af_value = value

    def set_em_mode(self, em: bool) -> None:
        self._session.em_enabled = em
    
    def set_sh_mode(self, sh: bool) -> None:
        self._session.sh_enabled = sh

    # ---------------------------
    # Lifecycle (interface)
    # ---------------------------

    def validate(self) -> ValidationResult:
        """
        Two-step validation, run in sequence:

        1. Session structural checks (e.g. AF value range, net name non-empty, etc).
           If errors exist, return immediately — no point running NQS checks.
        2. NQS-aware checks via ``validate`` (bus expansion mismatches,
           missing nets, non-canonical names, template existence, …).

        Callers only see a single ValidationResult.  Errors mean "do not
        commit"; warnings mean "committed but worth surfacing".
        """
        session_result = self._session.validate()
        if not session_result:
            return session_result

        return validate(self.to_line_data(), nqs=self._nqs)

    def to_line_data(self) -> AfLineData:
        """
        Serialize current session state into a typed line data object.
        """
        return self._session.to_line_data()

    def from_line_data(self, data: AfLineData) -> None:
        """
        Hydrate session state from an existing line (edit flow).
        """
        self._session.template_name = data.template
        self._session.template_regex_mode = data.is_template_regex
        self._session.net_name = data.net
        self._session.net_regex_mode = data.is_net_regex
        self._session.af_value = data.af_value
        self._session.em_enabled = data.is_em_enabled
        self._session.sh_enabled = data.is_sh_enabled
