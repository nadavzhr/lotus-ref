"""
NetSpec — a lightweight descriptor for a (template, net) resolution pair.

Every LineData type exposes ``net_specs() -> list[NetSpec]`` so that
conflict detection can resolve nets generically without ``isinstance``
checks on concrete data classes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class NetSpec:
    """One (template, net, regex-flags) tuple to resolve against the netlist."""
    template: Optional[str]
    net: str
    is_template_regex: bool
    is_net_regex: bool
