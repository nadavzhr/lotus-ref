"""
Parser for Activity Factor configuration lines.

Line format: {template:net} AF_VALUE flags   or   {net} AF_VALUE flags
"""
from __future__ import annotations

import re

from doc_types.af.line_data import AfLineData


# ---- shared constants (parser + serializer) ----

FLAG_EM = "em"
FLAG_SH = "sh"
FLAG_SCH = "sch"
FLAG_NET_REGEXP = "net-regexp"
FLAG_NET_REGULAR = "net-regular"
FLAG_TEMPLATE_REGEXP = "template-regexp"
FLAG_TEMPLATE_REGULAR = "template-regular"
FLAG_SEPARATOR = "_"
COMMENT_INDICATOR = "#"

CFG_OPTIONS = {
    FLAG_NET_REGEXP, FLAG_NET_REGULAR,
    FLAG_TEMPLATE_REGEXP, FLAG_TEMPLATE_REGULAR,
    FLAG_EM, FLAG_SH, FLAG_SCH,
}
NET_OPTIONS = {FLAG_NET_REGEXP, FLAG_NET_REGULAR}
TEMPLATE_OPTIONS = {FLAG_TEMPLATE_REGEXP, FLAG_TEMPLATE_REGULAR}

_BUS_RE = re.compile(r"\[\d+[:\-]\d+\]")


def is_comment(text: str) -> bool:
    return text.strip().startswith(COMMENT_INDICATOR)


def is_empty(text: str) -> bool:
    return not text.strip()


def parse(text: str) -> AfLineData:
    """
    Parse an AF configuration line into a typed AfLineData.

    Raises ValueError on structurally invalid lines.
    Comments and blank lines should be checked by the caller before
    calling parse() — they are not AF data lines.
    """
    content = text.strip()
    parts = content.split()
    if len(parts) != 3:
        raise ValueError("AF line must contain exactly 3 whitespace-separated fields")

    raw_name, af_text, cfg_text = parts

    # ---- name field ----
    if not raw_name:
        raise ValueError("Name field cannot be empty")

    is_braced = raw_name.startswith("{") and raw_name.endswith("}")
    has_partial = (
        (raw_name.startswith("{") and not raw_name.endswith("}"))
        or (not raw_name.startswith("{") and raw_name.endswith("}"))
    )
    if has_partial:
        raise ValueError("Unbalanced braces in name field")
    if ("{" in raw_name or "}" in raw_name) and not is_braced:
        raise ValueError("Braces are only allowed as a single outer pair around name")

    name = raw_name[1:-1] if is_braced else raw_name
    if not name:
        raise ValueError("Name inside braces cannot be empty")

    # ---- AF value ----
    try:
        af_value = float(af_text)
    except ValueError as exc:
        raise ValueError(f"Invalid AF value: {af_text}") from exc

    # ---- cfg flags ----
    cfg_list = cfg_text.split(FLAG_SEPARATOR)
    if not cfg_list or any(not f for f in cfg_list):
        raise ValueError("cfg_options cannot contain empty tokens")

    invalid = [f for f in cfg_list if f not in CFG_OPTIONS]
    if invalid:
        raise ValueError(f"Invalid cfg option(s): {', '.join(invalid)}")

    dupes = sorted({f for f in cfg_list if cfg_list.count(f) > 1})
    if dupes:
        raise ValueError(f"Duplicate cfg option(s): {', '.join(dupes)}")

    net_modes = [f for f in cfg_list if f in NET_OPTIONS]
    if not net_modes:
        raise ValueError("Missing required net option (net-regexp or net-regular)")
    if len(net_modes) > 1:
        raise ValueError("Only one net option is allowed")

    template_modes = [f for f in cfg_list if f in TEMPLATE_OPTIONS]
    if len(template_modes) > 1:
        raise ValueError("Only one template option is allowed")

    is_net_regex = net_modes[0] == FLAG_NET_REGEXP
    is_template_regex = (template_modes[0] == FLAG_TEMPLATE_REGEXP) if template_modes else False

    is_sch_enabled = FLAG_SCH in cfg_list
    is_em_enabled = FLAG_EM in cfg_list
    is_sh_enabled = FLAG_SH in cfg_list

    # default: both enabled when neither specified
    if not is_em_enabled and not is_sh_enabled:
        is_em_enabled = True
        is_sh_enabled = True

    # ---- template / net split ----
    template_needed = len(template_modes) == 1
    template_name: str | None = None
    net_name = name
    if template_needed:
        name_no_bus = _BUS_RE.sub("", name)
        if name_no_bus.count(":") != 1:
            raise ValueError("Template mode requires exactly one ':' in name (ignoring bus notation)")
        template_name, net_name = name.split(":", 1)
        if not template_name or not net_name:
            raise ValueError("Template mode requires non-empty template and net names")

    return AfLineData(
        template=template_name,
        net=net_name,
        af_value=af_value,
        is_template_regex=is_template_regex,
        is_net_regex=is_net_regex,
        is_em_enabled=is_em_enabled,
        is_sh_enabled=is_sh_enabled,
        is_sch_enabled=is_sch_enabled,
    )
