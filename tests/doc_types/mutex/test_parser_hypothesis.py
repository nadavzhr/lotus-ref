"""
Hypothesis property-based tests for Mutex parse ↔ serialize round-trip.

The core property: for any well-formed MutexLineData, serializing to text
and re-parsing must yield the same data.
"""
from __future__ import annotations

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from doc_types.mutex.line_data import MutexLineData, FEVMode
from doc_types.mutex.parser import parse
from doc_types.mutex.serializer import serialize


# ------------------------------------------------------------------
# Strategies
# ------------------------------------------------------------------

# Identifiers suitable for net/template names — no whitespace, no commas
_IDENT_CHARS = st.sampled_from(
    "abcdefghijklmnopqrstuvwxyz0123456789_/"
)
_ident = st.text(_IDENT_CHARS, min_size=1, max_size=15)

# Template: either None or a non-empty identifier
_template = st.one_of(st.none(), _ident)

# FEV modes
_fev = st.sampled_from(list(FEVMode))

# Mutexed nets: 1+ net names (no whitespace, no commas in individual names)
_mutexed_nets = st.lists(_ident, min_size=1, max_size=5).map(tuple)

# Active nets: can be empty or 1+ names
_active_nets = st.lists(_ident, min_size=0, max_size=3).map(tuple)


@st.composite
def mutex_line_data(draw: st.DrawFn) -> MutexLineData:
    """Generate a well-formed MutexLineData that survives round-trip."""
    template = draw(_template)
    fev = draw(_fev)
    num_active = draw(st.integers(min_value=1, max_value=9))

    # is_net_regex only matters when there is no template
    # (with template, the serializer writes "template ..." not "regexp/regular")
    is_net_regex = draw(st.booleans()) if template is None else False

    mutexed = draw(_mutexed_nets)
    active = draw(_active_nets)

    # Ensure active nets don't contain commas (they would be split on round-trip)
    # Our _ident strategy already excludes commas

    # Filter: "on=" prefix in the last mutexed net would be ambiguous
    assume(not any(n.startswith("on=") for n in mutexed))

    return MutexLineData(
        num_active=num_active,
        fev=fev,
        is_net_regex=is_net_regex,
        template=template,
        mutexed_nets=mutexed,
        active_nets=active,
    )


# ------------------------------------------------------------------
# Properties
# ------------------------------------------------------------------


class TestMutexRoundTrip:
    @given(data=mutex_line_data())
    @settings(max_examples=200)
    def test_parse_of_serialize_is_identity(self, data: MutexLineData):
        """parse(serialize(d)) == d for all well-formed MutexLineData."""
        text = serialize(data)
        restored = parse(text)

        assert restored.num_active == data.num_active
        assert restored.fev == data.fev
        assert restored.template == data.template
        assert restored.mutexed_nets == data.mutexed_nets
        assert restored.active_nets == data.active_nets

    @given(data=mutex_line_data())
    @settings(max_examples=200)
    def test_serialize_is_deterministic(self, data: MutexLineData):
        """Serializing the same data twice must yield identical text."""
        assert serialize(data) == serialize(data)
