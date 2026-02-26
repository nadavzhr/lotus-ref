import pytest

from doc_types.af import AfLineData, serializer as af_serializer, parser as af_parser
# ===========================================================
# Serialization
# ===========================================================

class TestAfSerializer:

    def test_simple_net(self):
        data = AfLineData(net="vdd", af_value=0.5, is_em_enabled=True, is_sh_enabled=True)
        result = af_serializer.serialize(data)
        assert result == "{vdd} 0.5 net-regular_em_sh"

    def test_template_net(self):
        data = AfLineData(
            template="T1", net="vdd", af_value=0.8,
            is_em_enabled=True, is_sh_enabled=False,
        )
        result = af_serializer.serialize(data)
        assert result == "{T1:vdd} 0.8 net-regular_template-regular_em"

    def test_regex_net(self):
        data = AfLineData(net="vdd.*", af_value=0.3, is_net_regex=True, is_sh_enabled=True)
        result = af_serializer.serialize(data)
        assert result == "{vdd.*} 0.3 net-regexp_sh"

    def test_template_regex(self):
        data = AfLineData(
            template="T.*", net="vdd", af_value=0.5,
            is_template_regex=True, is_em_enabled=True, is_sh_enabled=True,
        )
        result = af_serializer.serialize(data)
        assert result == "{T.*:vdd} 0.5 net-regular_template-regexp_em_sh"

    def test_sch_flag(self):
        data = AfLineData(
            net="vdd", af_value=0.5, is_sch_enabled=True,
            is_em_enabled=True, is_sh_enabled=False,
        )
        result = af_serializer.serialize(data)
        assert result == "{vdd} 0.5 net-regular_sch_em"

    def test_no_modes_defaults_both(self):
        data = AfLineData(net="vdd", af_value=0.5)
        result = af_serializer.serialize(data)
        assert "em" in result and "sh" in result

    def test_empty_net_raises(self):
        with pytest.raises(ValueError, match="net is required"):
            af_serializer.serialize(AfLineData())


# ===========================================================
# Round-trip: parse → serialize → parse
# ===========================================================

class TestAfRoundTrip:

    @pytest.mark.parametrize("line", [
        "{vdd} 0.5 net-regular_em_sh",
        "{T1:vdd} 0.8 net-regular_template-regular_em",
        "{vdd.*} 0.3 net-regexp_em_sh",
        "{T.*:vdd} 0.5 net-regular_template-regexp_em_sh",
        "{vdd} 0.5 net-regular_sch_em_sh",
    ])
    def test_round_trip(self, line):
        data = af_parser.parse(line)
        serialized = af_serializer.serialize(data)
        reparsed = af_parser.parse(serialized)
        assert data == reparsed
