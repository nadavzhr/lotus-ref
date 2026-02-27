from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.net_spec import NetSpec


@dataclass(slots=True)
class AfLineData:
    """Typed representation of a single AF configuration line."""
    template: Optional[str] = None
    net: str = ""
    af_value: float = 0.0
    is_template_regex: bool = False
    is_net_regex: bool = False
    is_em_enabled: bool = False
    is_sh_enabled: bool = False
    is_sch_enabled: bool = False

    def net_specs(self) -> list[NetSpec]:
        """Return the single (template, net) pair for conflict detection."""
        return [NetSpec(self.template, self.net, self.is_template_regex, self.is_net_regex)]
