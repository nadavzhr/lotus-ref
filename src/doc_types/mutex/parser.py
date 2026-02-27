"""
Parser for Mutex configuration lines.

Line format: mutex<N>[_suffix] <type> <nets> [on=<active>]
"""
from __future__ import annotations

import re

from doc_types.mutex.line_data import MutexLineData, FEVMode


COMMENT_INDICATOR = "#"

_MUTEX_LINE_RE = re.compile(
    r"^mutex(?P<mutex_num>\d+)"
    r"(?:_(?P<fev_suffix>low|high|ignore))?"
    r"(?:"
        r"(?:\s+template(?:_sch)?\s+(?P<template_name>\S+))"
        r"|"
        r"(?:\s+(?P<is_regexp>regular|regexp)(?:_sch)?)"
    r")"
    r"\s+(?P<mutexed_nets>.+?)"
    r"(?:\s+on=(?P<active_nets>.+))?$"
)


def is_comment(text: str) -> bool:
    return text.strip().startswith(COMMENT_INDICATOR)


def is_empty(text: str) -> bool:
    return not text.strip()


def parse(text: str) -> MutexLineData:
    """
    Parse a Mutex configuration line into a typed MutexLineData.

    Raises ValueError on structurally invalid lines.
    Comments and blank lines should be checked by the caller first.
    """
    content = text.strip()
    match = _MUTEX_LINE_RE.match(content)
    if not match:
        raise ValueError("Line does not match the expected Mutex format")

    active_str = match.group("active_nets")
    active_nets = (
        [n.strip() for n in active_str.split(",")]
        if active_str
        else []
    )

    fev_str = match.group("fev_suffix") or ""
    return MutexLineData(
        num_active=int(match.group("mutex_num")),
        fev=FEVMode(fev_str),
        is_net_regex=match.group("is_regexp") == "regexp",
        template=match.group("template_name") or None,
        mutexed_nets=tuple(n.strip() for n in match.group("mutexed_nets").split()),
        active_nets=tuple(active_nets),
    )
