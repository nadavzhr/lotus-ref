"""
Serializer for Mutex configuration lines.

Converts MutexLineData back to config file text format, and provides
JSON round-trip helpers (``from_dict`` / ``to_json``).
"""
from __future__ import annotations

import dataclasses

from doc_types.mutex.line_data import MutexLineData, FEVMode


def serialize(data: MutexLineData) -> str:
    """Serialize a MutexLineData into a single config line string."""
    parts = [f"mutex{data.num_active}"]

    # FEV suffix (_low, _high, _ignore, or empty)
    fev_suffix = data.fev.value
    parts.append(f"_{fev_suffix}" if fev_suffix != FEVMode.EMPTY.value else "")

    # Type: template or regexp/regular
    if data.template is not None:
        parts.append(f" template {data.template}")
    else:
        parts.append(f" {'regexp' if data.is_net_regex else 'regular'}")

    # Mutexed nets (space-separated)
    parts.append(" " + " ".join(data.mutexed_nets))

    # Active nets (comma-separated with on=)
    if data.active_nets:
        parts.append(f" on={','.join(data.active_nets)}")

    return "".join(parts)


def from_dict(fields: dict) -> MutexLineData:
    """Build a MutexLineData from a raw JSON dict."""
    fev_raw = fields.get("fev", "")
    template = fields.get("template", "")
    if template == "":
        template = None
    return MutexLineData(
        num_active=int(fields.get("num_active", 1)),
        fev=FEVMode(fev_raw) if fev_raw else FEVMode.EMPTY,
        is_net_regex=bool(fields.get("is_net_regex", False)),
        template=template,
        mutexed_nets=tuple(fields.get("mutexed_nets", ())),
        active_nets=tuple(fields.get("active_nets", ())),
    )


def to_json(data: MutexLineData) -> dict:
    """Convert MutexLineData to a JSON-safe dict (FEV enum → string)."""
    d = dataclasses.asdict(data)
    d["fev"] = data.fev.value
    return d
