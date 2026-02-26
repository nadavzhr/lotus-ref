from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

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
    is_regexp: bool = False
    template: Optional[str] = None
    mutexed_nets: list[str] = field(default_factory=list)
    active_nets: list[str] = field(default_factory=list)
