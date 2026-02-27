from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Optional


@dataclass(frozen=True, slots=True)
class MutexEntry:
    net_name: str
    regex_mode: bool = False
    template_name: Optional[str] = None
    matches: FrozenSet[str] = frozenset()

    def __post_init__(self):
        """
        Ensure matches is always stored as a frozenset
        for immutability and hash safety.
        """
        object.__setattr__(self, "matches", frozenset(self.matches))

    def intersects(self, other: "MutexEntry") -> bool:
        """
        Returns True if the resolved match sets overlap.
        """
        return bool(self.matches & other.matches)

    def __str__(self):
        template_part = f"{self.template_name}:" if self.template_name else ""
        return f"MutexEntry({template_part}{self.net_name}, regex={self.regex_mode})"
