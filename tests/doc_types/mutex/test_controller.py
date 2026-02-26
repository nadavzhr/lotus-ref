import pytest

from doc_types.mutex import MutexLineData, FEVMode, MutexEditController
from doc_types.mutex.exceptions import *
from tests.mock_nqs import MockNetlistQueryService


@pytest.fixture
def nqs():
    svc = MockNetlistQueryService()
    # Common exact-net mappings used across most tests
    for name in ("net1", "net2", "net3"):
        svc.canonical_map[(name, "T1")] = name
    svc.canonical_map[("VDD", "T1")] = "vdd"
    # Common bus notation expansion
    for i in range(3):
        svc.canonical_map[(f"bus[{i}]", "T1")] = f"bus[{i}]"
    # Common regex results
    svc.net_matches[("T1", "vdd.*", True)] = ["vdd1", "vdd2"]
    return svc


@pytest.fixture
def ctrl(nqs):
    c = MutexEditController(nqs)
    c.start_session("s1")
    return c


# ===========================================================
# Session lifecycle
# ===========================================================

class TestMutexControllerSessionLifecycle:

    def test_fresh_controller_has_empty_session(self, nqs):
        c = MutexEditController(nqs)
        assert len(c.session.mutexed_entries) == 0

    def test_start_session_replaces_old(self, nqs):
        c = MutexEditController(nqs)
        c.start_session("s1")
        c.add_mutexed("T1", "net1")
        c.start_session("s2")
        assert len(c.session.mutexed_entries) == 0  # fresh session


# ===========================================================
# add_mutexed — exact net
# ===========================================================

class TestMutexControllerAddMutexed:

    def test_add_exact_net(self, ctrl, nqs):
        ctrl.add_mutexed("T1", "net1")
        assert len(ctrl.session.mutexed_entries) == 1
        entry = next(iter(ctrl.session.mutexed_entries))
        assert entry.net_name == "net1"
        assert entry.matches == frozenset(["net1"])

    def test_add_exact_net_canonical_resolution(self, ctrl, nqs):
        ctrl.add_mutexed("T1", "VDD")
        entry = next(iter(ctrl.session.mutexed_entries))
        assert entry.matches == frozenset(["vdd"])

    def test_add_exact_net_no_canonical_uses_no_matches(self, ctrl, nqs):
        # No canonical mapping for 'unknown' → empty matches → NoMatchesError
        with pytest.raises(NoMatchesError):
            ctrl.add_mutexed("T1", "unknown")

    def test_add_duplicate_raises(self, ctrl, nqs):
        ctrl.add_mutexed("T1", "net1")
        with pytest.raises(DuplicateEntryError):
            ctrl.add_mutexed("T1", "net1")


# ===========================================================
# add_mutexed — regex
# ===========================================================

class TestMutexControllerAddMutexedRegex:

    def test_add_regex_pattern(self, ctrl, nqs):
        ctrl.add_mutexed("T1", "vdd.*", is_regex=True)
        entry = next(iter(ctrl.session.mutexed_entries))
        assert entry.regex_mode is True
        assert entry.matches == frozenset(["vdd1", "vdd2"])

    def test_add_regex_no_match_raises(self, ctrl, nqs):
        # find_matches returns empty → matches is empty → session raises NoMatchesError
        nqs.net_matches[("T1", "xxx.*", True)] = []
        with pytest.raises(NoMatchesError):
            ctrl.add_mutexed("T1", "xxx.*", is_regex=True)


# ===========================================================
# add_mutexed — bus notation
# ===========================================================

class TestMutexControllerAddMutexedBus:

    def test_add_bus_notation(self, ctrl, nqs):
        ctrl.add_mutexed("T1", "bus[0:2]")
        entry = next(iter(ctrl.session.mutexed_entries))
        assert entry.matches == frozenset(["bus[0]", "bus[1]", "bus[2]"])


# ===========================================================
# add_active
# ===========================================================

class TestMutexControllerAddActive:

    def test_add_active(self, ctrl, nqs):
        ctrl.add_active("T1", "net1")
        assert len(ctrl.session.active_entries) == 1
        assert len(ctrl.session.mutexed_entries) == 1

    def test_add_active_duplicate_raises(self, ctrl, nqs):
        ctrl.add_active("T1", "net1")
        with pytest.raises(DuplicateEntryError):
            ctrl.add_active("T1", "net1")


# ===========================================================
# remove
# ===========================================================

class TestMutexControllerRemove:

    def test_remove_mutexed(self, ctrl, nqs):
        ctrl.add_mutexed("T1", "net1")
        ctrl.add_mutexed("T1", "net2")
        ctrl.remove_mutexed("T1", "net1")
        assert len(ctrl.session.mutexed_entries) == 1

    def test_remove_active(self, ctrl, nqs):
        ctrl.add_active("T1", "net1")
        ctrl.remove_active("T1", "net1")
        assert len(ctrl.session.active_entries) == 0
        assert len(ctrl.session.mutexed_entries) == 1  # still mutexed

    def test_remove_nonexistent_raises(self, ctrl, nqs):
        with pytest.raises(EntryNotFoundError):
            ctrl.remove_mutexed("T1", "net1")

    def test_remove_active_nonexistent_raises(self, ctrl, nqs):
        with pytest.raises(EntryNotFoundError):
            ctrl.remove_active("T1", "net1")


# ===========================================================
# validate
# ===========================================================

class TestMutexControllerValidate:

    def test_validate_empty_invalid(self, ctrl):
        result = ctrl.validate()
        assert not result

    def test_validate_valid(self, ctrl, nqs):
        ctrl.add_mutexed("T1", "net1")
        ctrl.add_mutexed("T1", "net2")
        result = ctrl.validate()
        assert result


# ===========================================================
# set_fev_mode
# ===========================================================

class TestMutexControllerSetFEVMode:

    def test_set_fev_mode(self, ctrl):
        ctrl.set_fev_mode(FEVMode.LOW)
        assert ctrl.session.fev == FEVMode.LOW

    def test_set_fev_mode_high(self, ctrl):
        ctrl.set_fev_mode(FEVMode.HIGH)
        assert ctrl.session.fev == FEVMode.HIGH

    def test_set_fev_mode_ignore(self, ctrl):
        ctrl.set_fev_mode(FEVMode.IGNORE)
        assert ctrl.session.fev == FEVMode.IGNORE

    def test_set_fev_mode_empty(self, ctrl):
        ctrl.set_fev_mode(FEVMode.LOW)
        ctrl.set_fev_mode(FEVMode.EMPTY)
        assert ctrl.session.fev == FEVMode.EMPTY

    def test_set_fev_mode_invalid_raises(self, ctrl):
        with pytest.raises(InvalidFEVModeError):
            ctrl.set_fev_mode("not_a_fev_mode")


# ===========================================================
# to_line_data / from_line_data
# ===========================================================

class TestMutexControllerSerialization:

    def test_to_line_data(self, ctrl, nqs):
        ctrl.add_mutexed("T1", "net1")
        ctrl.add_active("T1", "net2")
        data = ctrl.to_line_data()
        assert isinstance(data, MutexLineData)
        assert data.template == "T1"
        assert data.is_regexp is False
        assert set(data.mutexed_nets) == {"net1", "net2"}
        assert data.active_nets == ["net2"]

    def test_to_line_data_includes_fev(self, ctrl, nqs):
        ctrl.set_fev_mode(FEVMode.HIGH)
        ctrl.add_mutexed("T1", "net1")
        ctrl.add_mutexed("T1", "net2")
        data = ctrl.to_line_data()
        assert data.fev == FEVMode.HIGH

    def test_to_line_data_num_active_from_active_entries(self, ctrl, nqs):
        ctrl.add_mutexed("T1", "net1")
        ctrl.add_active("T1", "net2")
        data = ctrl.to_line_data()
        assert data.num_active == 1

    def test_from_line_data_round_trip(self, nqs):
        # Build original
        ctrl1 = MutexEditController(nqs)
        ctrl1.start_session("s1")
        ctrl1.set_fev_mode(FEVMode.LOW)
        ctrl1.add_mutexed("T1", "net1")
        ctrl1.add_mutexed("T1", "net2")
        ctrl1.add_active("T1", "net3")
        data = ctrl1.to_line_data()

        # Hydrate into new controller
        ctrl2 = MutexEditController(nqs)
        ctrl2.start_session("s2")
        ctrl2.from_line_data(data)
        assert len(ctrl2.session.mutexed_entries) == 3
        assert len(ctrl2.session.active_entries) == 1
        assert ctrl2.session.fev == FEVMode.LOW

    def test_from_line_data_without_active_preserves_num_active(self, nqs):
        data = MutexLineData(
            num_active=2,
            fev=FEVMode.IGNORE,
            is_regexp=False,
            template="T1",
            mutexed_nets=["net1", "net2", "net3"],
            active_nets=[],
        )
        ctrl = MutexEditController(nqs)
        ctrl.start_session("s1")
        ctrl.from_line_data(data)
        assert ctrl.session.num_active == 2
        assert ctrl.session.fev == FEVMode.IGNORE
