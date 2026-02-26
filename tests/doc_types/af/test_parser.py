import pytest

from doc_types.af import AfLineData, parser as af_parser
# ===========================================================
# is_comment / is_empty
# ===========================================================

class TestAfParserTrivial:

    def test_comment(self):
        assert af_parser.is_comment("# this is a comment")

    def test_not_comment(self):
        assert not af_parser.is_comment("{vdd} 0.5 net-regular_em_sh")

    def test_empty(self):
        assert af_parser.is_empty("")
        assert af_parser.is_empty("   ")

    def test_not_empty(self):
        assert not af_parser.is_empty("{vdd} 0.5 net-regular_em_sh")


# ===========================================================
# Successful parsing
# ===========================================================

class TestAfParserSuccess:

    def test_simple_net_regular(self):
        data = af_parser.parse("{vdd} 0.5 net-regular_em_sh")
        assert data.template is None
        assert data.net == "vdd"
        assert data.af_value == 0.5
        assert data.is_net_regex is False
        assert data.is_em_enabled is True
        assert data.is_sh_enabled is True

    def test_template_net(self):
        data = af_parser.parse("{T1:vdd} 0.8 net-regular_template-regular_em")
        assert data.template == "T1"
        assert data.net == "vdd"
        assert data.af_value == 0.8
        assert data.is_template_regex is False
        assert data.is_em_enabled is True
        assert data.is_sh_enabled is False

    def test_regex_net(self):
        data = af_parser.parse("{vdd.*} 0.3 net-regexp_sh")
        assert data.net == "vdd.*"
        assert data.is_net_regex is True
        assert data.is_em_enabled is False
        assert data.is_sh_enabled is True

    def test_template_regex(self):
        data = af_parser.parse("{T.*:vdd} 0.5 net-regular_template-regexp_em_sh")
        assert data.template == "T.*"
        assert data.is_template_regex is True

    def test_sch_flag(self):
        data = af_parser.parse("{vdd} 0.5 net-regular_sch_em")
        assert data.is_sch_enabled is True

    def test_no_em_no_sh_defaults_both(self):
        data = af_parser.parse("{vdd} 0.5 net-regular_sch")
        assert data.is_em_enabled is True
        assert data.is_sh_enabled is True

    def test_af_value_zero(self):
        data = af_parser.parse("{vdd} 0 net-regular_em")
        assert data.af_value == 0.0

    def test_af_value_one(self):
        data = af_parser.parse("{vdd} 1 net-regular_em")
        assert data.af_value == 1.0

    def test_bus_notation_in_net(self):
        data = af_parser.parse("{T1:net[0:3]} 0.5 net-regular_template-regular_em")
        assert data.template == "T1"
        assert data.net == "net[0:3]"


# ===========================================================
# Parse errors
# ===========================================================

class TestAfParserErrors:

    def test_too_few_fields(self):
        with pytest.raises(ValueError, match="exactly 3"):
            af_parser.parse("{vdd} 0.5")

    def test_too_many_fields(self):
        with pytest.raises(ValueError, match="exactly 3"):
            af_parser.parse("{vdd} 0.5 net-regular extra")

    def test_unbalanced_brace(self):
        with pytest.raises(ValueError, match="Unbalanced"):
            af_parser.parse("{vdd 0.5 net-regular_em")

    def test_empty_braces(self):
        with pytest.raises(ValueError, match="empty"):
            af_parser.parse("{} 0.5 net-regular_em")

    def test_invalid_af_value(self):
        with pytest.raises(ValueError, match="Invalid AF"):
            af_parser.parse("{vdd} abc net-regular_em")

    def test_invalid_cfg_option(self):
        with pytest.raises(ValueError, match="Invalid cfg"):
            af_parser.parse("{vdd} 0.5 net-regular_bogus")

    def test_duplicate_cfg_option(self):
        with pytest.raises(ValueError, match="Duplicate"):
            af_parser.parse("{vdd} 0.5 net-regular_em_em")

    def test_missing_net_option(self):
        with pytest.raises(ValueError, match="Missing required net"):
            af_parser.parse("{vdd} 0.5 em_sh")

    def test_both_net_options(self):
        with pytest.raises(ValueError, match="Only one net"):
            af_parser.parse("{vdd} 0.5 net-regular_net-regexp_em")

    def test_template_mode_missing_colon(self):
        with pytest.raises(ValueError, match="exactly one ':'"):
            af_parser.parse("{vdd} 0.5 net-regular_template-regular_em")
