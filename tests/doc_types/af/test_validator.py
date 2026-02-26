import pytest

from doc_types.af import AfLineData, validate_af
from core import ValidationResult
from tests.mock_nqs import MockNetlistQueryService


# ===========================================================
# Layer 2: domain-only (no service)
# ===========================================================

class TestAfValidatorDomain:

    def test_valid_data(self):
        data = AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)
        result = validate_af(data)
        assert result.is_valid
        assert result.errors == []

    def test_empty_net(self):
        data = AfLineData(af_value=0.5, is_em_enabled=True)
        result = validate_af(data)
        assert not result.is_valid
        assert any("net name" in e.lower() for e in result.errors)

    def test_af_below_zero(self):
        data = AfLineData(net="vdd", af_value=-0.1, is_em_enabled=True)
        result = validate_af(data)
        assert not result.is_valid
        assert any("between 0 and 1" in e for e in result.errors)

    def test_af_above_one(self):
        data = AfLineData(net="vdd", af_value=1.5, is_em_enabled=True)
        result = validate_af(data)
        assert not result.is_valid

    def test_af_at_boundaries(self):
        assert validate_af(AfLineData(net="vdd", af_value=0.0, is_em_enabled=True)).is_valid
        assert validate_af(AfLineData(net="vdd", af_value=1.0, is_em_enabled=True)).is_valid

    def test_no_mode_selected(self):
        data = AfLineData(net="vdd", af_value=0.5)
        result = validate_af(data)
        assert not result.is_valid
        assert any("em or sh" in e.lower() for e in result.errors)

    def test_multiple_errors(self):
        data = AfLineData()  # empty net, no mode
        result = validate_af(data)
        assert len(result.errors) >= 2


# ===========================================================
# Layer 3: netlist validation (with service)
# ===========================================================

@pytest.fixture
def nqs():
    svc = MockNetlistQueryService()
    svc.templates = {"T1"}
    svc.canonical_map[("vdd", "T1")] = "vdd"
    svc.canonical_map[("VDD", "T1")] = "vdd"
    svc.canonical_map[("vdd", None)] = "vdd"
    svc.net_matches[("T1", "vdd", False)] = ["vdd"]
    svc.net_matches[(None, "vdd", False)] = ["vdd"]
    svc.net_matches[("T1", "vdd.*", True)] = ["vdd1", "vdd2"]
    return svc


class TestAfValidatorNetlist:

    def test_valid_with_matches(self, nqs):
        data = AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)
        result = validate_af(data, nqs=nqs)
        assert result.is_valid
        assert result.warnings == []

    def test_no_matches_warning(self, nqs):
        data = AfLineData(net="nonexistent", af_value=0.5, is_em_enabled=True)
        result = validate_af(data, nqs=nqs)
        assert result.is_valid  # warnings don't block
        assert any("no matches" in w.lower() for w in result.warnings)

    def test_canonical_name_warning(self, nqs):
        nqs.net_matches[("T1", "VDD", False)] = ["vdd"]
        data = AfLineData(
            template="T1", net="VDD", af_value=0.5, is_em_enabled=True,
        )
        result = validate_af(data, nqs=nqs)
        assert result.is_valid
        assert any("not canonical" in w.lower() for w in result.warnings)

    def test_template_not_found_warning(self, nqs):
        data = AfLineData(
            template="MISSING", net="vdd", af_value=0.5, is_em_enabled=True,
        )
        result = validate_af(data, nqs=nqs)
        assert result.is_valid
        assert any("does not exist" in w.lower() for w in result.warnings)

    def test_domain_errors_skip_netlist(self, nqs):
        """When domain errors exist, netlist checks are skipped."""
        data = AfLineData(net="", af_value=0.5, is_em_enabled=True)
        result = validate_af(data, nqs=nqs)
        assert not result.is_valid
        assert result.warnings == []  # no netlist warnings attempted

    def test_bus_width_warning(self, nqs):
        # net[0:3] expands to 4 bits, but only 2 match
        nqs.net_matches[(None, "net[0:3]", False)] = ["net[0]", "net[1]"]
        data = AfLineData(net="net[0:3]", af_value=0.5, is_em_enabled=True)
        result = validate_af(data, nqs=nqs)
        assert result.is_valid
        assert any("larger than existing" in w.lower() for w in result.warnings)
