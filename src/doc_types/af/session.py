from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from doc_types.af.line_data import AfLineData
from core.validation_result import ValidationResult
from core.interfaces import IEditSessionState
from doc_types.af import validator


@dataclass(slots=True)
class AfEditSessionState(IEditSessionState):
    session_id: str
    template_name: Optional[str] = None
    template_regex_mode: bool = False
    net_name: str = ""
    net_regex_mode: bool = False
    em_enabled: bool = False
    sh_enabled: bool = False
    af_value: float = 0.0

    def to_line_data(self) -> AfLineData:
        """Convert session state into the shared typed data object."""
        return AfLineData(
            template=self.template_name,
            net=self.net_name,
            af_value=self.af_value,
            is_template_regex=self.template_regex_mode,
            is_net_regex=self.net_regex_mode,
            is_em_enabled=self.em_enabled,
            is_sh_enabled=self.sh_enabled,
        )

    def validate(self) -> ValidationResult:
        """Domain-only (Layer 2) validation without netlist service.

        Delegates to the shared AF validator so rules are defined once.
        NQS-aware validation (Layer 3) runs via the controller's
        ``validate()`` method, which passes the service explicitly.
        """
        return validator.validate(self.to_line_data())
