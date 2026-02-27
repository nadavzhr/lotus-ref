"""
Serializer for Activity Factor configuration lines.

Converts AfLineData back to config file text format, and provides
JSON round-trip helpers (``from_dict`` / ``to_json``).
"""
from __future__ import annotations

import dataclasses

from doc_types.af.line_data import AfLineData
from doc_types.af.parser import (
    FLAG_EM, FLAG_SH, FLAG_SCH,
    FLAG_NET_REGEXP, FLAG_NET_REGULAR,
    FLAG_TEMPLATE_REGEXP, FLAG_TEMPLATE_REGULAR,
    FLAG_SEPARATOR,
)


def serialize(data: AfLineData) -> str:
    """Serialize an AfLineData into a single config line string."""
    if not data.net:
        raise ValueError("net is required for AF serialization")

    is_em = data.is_em_enabled
    is_sh = data.is_sh_enabled
    # If both disabled, treat as both enabled
    if not is_em and not is_sh:
        is_em = True
        is_sh = True

    flags: list[str] = []

    # net regex flag (required)
    flags.append(FLAG_NET_REGEXP if data.is_net_regex else FLAG_NET_REGULAR)

    # template regex flag (only when template is set)
    if data.template is not None:
        flags.append(FLAG_TEMPLATE_REGEXP if data.is_template_regex else FLAG_TEMPLATE_REGULAR)

    # feature flags
    if data.is_sch_enabled:
        flags.append(FLAG_SCH)
    if is_em:
        flags.append(FLAG_EM)
    if is_sh:
        flags.append(FLAG_SH)

    cfg_str = FLAG_SEPARATOR.join(flags)

    # name field
    if data.template is not None:
        name = f"{{{data.template}:{data.net}}}"
    else:
        name = f"{{{data.net}}}"

    return f"{name} {data.af_value} {cfg_str}"


def from_dict(fields: dict) -> AfLineData:
    """Build an AfLineData from a raw JSON dict."""
    template = fields.get("template", "")
    if template == "":
        template = None
    return AfLineData(
        template=template,
        net=fields.get("net", ""),
        af_value=float(fields.get("af_value", 0.0)),
        is_template_regex=bool(fields.get("is_template_regex", False)),
        is_net_regex=bool(fields.get("is_net_regex", False)),
        is_em_enabled=bool(fields.get("is_em_enabled", False)),
        is_sh_enabled=bool(fields.get("is_sh_enabled", False)),
        is_sch_enabled=bool(fields.get("is_sch_enabled", False)),
    )


def to_json(data: AfLineData) -> dict:
    """Convert AfLineData to a JSON-safe dict."""
    return dataclasses.asdict(data)
