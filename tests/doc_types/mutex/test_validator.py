import pytest

from doc_types.mutex import MutexLineData, FEVMode, validator
from core import ValidationResult
from tests.mock_nqs import MockNetlistQueryService


# ===========================================================
# Layer 2: domain-only (no service)
# ===========================================================

class TestMutexValidatorDomain:

    def test_valid_data(self):
        data = MutexLineData(num_active=2, mutexed_nets=["net1", "net2"])
        result = validator.validate(data)
        assert result.is_valid

    def test_empty_mutexed_nets(self):
        data = MutexLineData(num_active=2, mutexed_nets=[])
        result = validator.validate(data)
        assert not result.is_valid
        assert any("no mutexed nets" in e.lower() for e in result.errors)

    def test_single_non_regex_net_ok(self):
        """Single non-regex net is valid at the domain level; netlist check catches too few matches."""
        data = MutexLineData(num_active=1, mutexed_nets=["net1"])
        result = validator.validate(data)
        assert result.is_valid

    def test_single_regex_net_ok(self):
        """Regex mode can have a single pattern that matches multiple nets."""
        data = MutexLineData(num_active=1, is_regexp=True, mutexed_nets=["vdd.*"])
        result = validator.validate(data)
        assert result.is_valid

    def test_active_count_mismatch(self):
        data = MutexLineData(
            num_active=2, mutexed_nets=["net1", "net2"],
            active_nets=["net1", "net2", "net3"],
        )
        result = validator.validate(data)
        assert not result.is_valid
        assert any("does not match" in e.lower() for e in result.errors)

    def test_active_count_matches(self):
        data = MutexLineData(
            num_active=2, mutexed_nets=["net1", "net2"],
            active_nets=["net1", "net2"],
        )
        result = validator.validate(data)
        assert result.is_valid

    def test_fev_mode_in_data(self):
        """FEVMode is stored in data and doesn't cause domain errors."""
        data = MutexLineData(
            num_active=2, fev=FEVMode.HIGH, mutexed_nets=["net1", "net2"],
        )
        result = validator.validate(data)
        assert result.is_valid


# ===========================================================
# Layer 3: netlist validation (with service)
# ===========================================================

@pytest.fixture
def nqs():
    svc = MockNetlistQueryService()
    svc.templates = {"T1"}
    for name in ("net1", "net2", "net3"):
        svc.canonical_map[(name, None)] = name
        svc.canonical_map[(name, "T1")] = name
    svc.net_matches[("T1", "vdd.*", True)] = ["vdd1", "vdd2"]
    return svc


class TestMutexValidatorNetlist:

    def test_valid_with_canonical(self, nqs):
        data = MutexLineData(num_active=2, mutexed_nets=["net1", "net2"])
        result = validator.validate(data, nqs=nqs)
        assert result.is_valid
        assert result.warnings == []

    def test_net_not_found_warning(self, nqs):
        data = MutexLineData(num_active=2, mutexed_nets=["net1", "unknown"])
        result = validator.validate(data, nqs=nqs)
        assert result.is_valid
        assert any("does not exist" in w.lower() for w in result.warnings)

    def test_canonical_name_warning(self, nqs):
        nqs.canonical_map[("VDD", None)] = "vdd"
        data = MutexLineData(num_active=2, mutexed_nets=["net1", "VDD"])
        result = validator.validate(data, nqs=nqs)
        assert any("not canonical" in w.lower() for w in result.warnings)

    def test_template_not_found_warning(self, nqs):
        data = MutexLineData(
            num_active=2, template="MISSING",
            mutexed_nets=["net1", "net2"],
        )
        result = validator.validate(data, nqs=nqs)
        assert any("does not exist" in w.lower() for w in result.warnings)

    def test_regex_no_matches_warning(self, nqs):
        data = MutexLineData(
            num_active=1, is_regexp=True, template="T1",
            mutexed_nets=["zzz.*"],
        )
        result = validator.validate(data, nqs=nqs)
        assert any("no matches" in w.lower() for w in result.warnings)

    def test_regex_with_matches(self, nqs):
        data = MutexLineData(
            num_active=1, is_regexp=True, template="T1",
            mutexed_nets=["vdd.*"],
        )
        result = validator.validate(data, nqs=nqs)
        assert not any("no matches" in w.lower() for w in result.warnings)

    def test_active_net_not_found_warning(self, nqs):
        data = MutexLineData(
            num_active=1, mutexed_nets=["net1", "net2"],
            active_nets=["unknown"],
        )
        result = validator.validate(data, nqs=nqs)
        assert any("active net" in w.lower() and "does not exist" in w.lower()
                    for w in result.warnings)

    def test_domain_errors_skip_netlist(self, nqs):
        """When domain errors exist, netlist checks are skipped."""
        data = MutexLineData(num_active=2, mutexed_nets=[])
        result = validator.validate(data, nqs=nqs)
        assert not result.is_valid
        assert result.warnings == []
