from typing import Optional

from doc_types.af.line_data import AfLineData
from core.validation_result import ValidationResult
from doc_types.af.session import AFEditSessionState
from core.interfaces import IEditController, INetlistQueryService
from doc_types.af.validator import validate_af


class AfEditController(IEditController[AfLineData]):

    def __init__(self, netlist_query_service: INetlistQueryService):
        self._nqs = netlist_query_service
        self._session = AFEditSessionState("")  # Initialize with an empty session; will be replaced on start_session

    # ---------------------------
    # Session lifecycle
    # ---------------------------

    def start_session(self, session_id: str) -> None:
        self._session = AFEditSessionState(session_id)

    # ---------------------------
    # Properties (read-only views)
    # ---------------------------

    @property
    def session(self) -> AFEditSessionState:
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
        Full validation: domain + netlist-level warnings.
        Delegates entirely to the shared validator with service.
        """
        return validate_af(self._session.to_line_data(), nqs=self._nqs)

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
