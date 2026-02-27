"""
Hypothesis property-based tests for AF parse ↔ serialize round-trip.

The core property: for any well-formed AfLineData, serializing to text
and re-parsing must yield the same data.
"""
from __future__ import annotations

from hypothesis import given, settings, assume
from hypothesis import strategies as st
import pytest

from doc_types.af.line_data import AfLineData
from doc_types.af.parser import parse
from doc_types.af.serializer import serialize


# ------------------------------------------------------------------
# Strategies
# ------------------------------------------------------------------

# Net / template names: printable, no whitespace, no braces, no colons
_IDENT_CHARS = st.sampled_from(
    "abcdefghijklmnopqrstuvwxyz0123456789_/.*"
)
_ident = st.text(_IDENT_CHARS, min_size=1, max_size=20)

# A safe net name (no colon so it doesn't clash with template:net split)
_net_name = _ident.filter(lambda s: ":" not in s)

# Template: either None or a non-empty identifier (no colon)
_template = st.one_of(st.none(), _net_name)

# AF value: positive finite float
_af_value = st.floats(
    min_value=0.0, max_value=1e6,
    allow_nan=False, allow_infinity=False,
    allow_subnormal=False,
)

# Feature flags
_bool = st.booleans()


@st.composite
def af_line_data(draw: st.DrawFn) -> AfLineData:
    """Generate a well-formed AfLineData that survives round-trip."""
    template = draw(_template)
    net = draw(_net_name)

    # If template is set, template_regex flag may be anything;
    # if template is None, is_template_regex must be False
    is_template_regex = draw(_bool) if template is not None else False

    is_net_regex = draw(_bool)
    is_em = draw(_bool)
    is_sh = draw(_bool)
    is_sch = draw(_bool)

    # The serializer normalises (em=False, sh=False) → (em=True, sh=True)
    if not is_em and not is_sh:
        is_em = True
        is_sh = True

    af_value = draw(_af_value)

    return AfLineData(
        template=template,
        net=net,
        af_value=af_value,
        is_template_regex=is_template_regex,
        is_net_regex=is_net_regex,
        is_em_enabled=is_em,
        is_sh_enabled=is_sh,
        is_sch_enabled=is_sch,
    )


# ------------------------------------------------------------------
# Properties
# ------------------------------------------------------------------


class TestAfRoundTrip:
    @given(data=af_line_data())
    @settings(max_examples=200)
    def test_parse_of_serialize_is_identity(self, data: AfLineData):
        """parse(serialize(d)) == d for all well-formed AfLineData."""
        text = serialize(data)
        restored = parse(text)

        assert restored.template == data.template
        assert restored.net == data.net
        assert restored.af_value == pytest.approx(data.af_value)
        assert restored.is_template_regex == data.is_template_regex
        assert restored.is_net_regex == data.is_net_regex
        assert restored.is_em_enabled == data.is_em_enabled
        assert restored.is_sh_enabled == data.is_sh_enabled
        assert restored.is_sch_enabled == data.is_sch_enabled

    @given(data=af_line_data())
    @settings(max_examples=200)
    def test_serialize_is_deterministic(self, data: AfLineData):
        """Serializing the same data twice must yield identical text."""
        assert serialize(data) == serialize(data)

    @given(data=af_line_data())
    @settings(max_examples=100)
    def test_serialized_text_has_three_fields(self, data: AfLineData):
        """Every valid serialisation has exactly 3 whitespace-separated fields."""
        text = serialize(data)
        assert len(text.split()) == 3
