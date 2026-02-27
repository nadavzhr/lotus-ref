from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from core.net_spec import NetSpec


class FEVMode(Enum):
    EMPTY = ""
    LOW = "low"
    HIGH = "high"
    IGNORE = "ignore"


@dataclass(slots=True)
class MutexLineData:
    """Typed representation of a single Mutex configuration line."""
    num_active: int = 1
    fev: FEVMode = FEVMode.EMPTY
    is_net_regex: bool = False
    template: Optional[str] = None
    mutexed_nets: tuple[str, ...] = field(default_factory=tuple)
    active_nets: tuple[str, ...] = field(default_factory=tuple)

    def net_specs(self) -> list[NetSpec]:
        """Return one spec per mutexed net for conflict detection."""
        return [
            NetSpec(self.template, net, False, self.is_net_regex)
            for net in self.mutexed_nets
        ]
