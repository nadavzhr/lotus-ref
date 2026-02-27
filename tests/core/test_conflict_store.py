import pytest

from core.conflict_store import ConflictStore, ConflictInfo, resolve_line_nets
from doc_types.af.line_data import AfLineData
from doc_types.mutex.line_data import MutexLineData, FEVMode
from tests.mock_nqs import MockNetlistQueryService


# ===========================================================
# ConflictStore — basic operations
# ===========================================================

class TestConflictStoreEmpty:

    def test_empty_store_no_conflict(self):
        store = ConflictStore()
        assert not store.is_conflicting("any")
        assert store.get_conflicting_lines("any") == set()
        assert store.get_conflicting_net_ids("any") == frozenset()
        assert store.get_conflict_info("any") is None

    def test_single_line_no_conflict(self):
        store = ConflictStore()
        store.update_line("L1", {100, 200})
        assert not store.is_conflicting("L1")
        assert store.get_conflicting_lines("L1") == set()
        assert store.get_conflicting_net_ids("L1") == frozenset()
        assert store.get_conflict_info("L1") is None


class TestConflictStoreDetection:

    def test_two_lines_same_net_conflict(self):
        store = ConflictStore()
        store.update_line("L1", {100, 200})
        store.update_line("L2", {100, 300})

        assert store.is_conflicting("L1")
        assert store.is_conflicting("L2")
        assert store.get_conflicting_lines("L1") == {"L2"}
        assert store.get_conflicting_lines("L2") == {"L1"}
        assert store.get_conflicting_net_ids("L1") == frozenset({100})
        assert store.get_conflicting_net_ids("L2") == frozenset({100})

    def test_no_overlap_no_conflict(self):
        store = ConflictStore()
        store.update_line("L1", {100})
        store.update_line("L2", {200})

        assert not store.is_conflicting("L1")
        assert not store.is_conflicting("L2")

    def test_three_lines_shared_net(self):
        store = ConflictStore()
        store.update_line("L1", {100})
        store.update_line("L2", {100, 300})
        store.update_line("L3", {100})

        assert store.is_conflicting("L1")
        assert store.get_conflicting_lines("L1") == {"L2", "L3"}
        assert store.get_conflicting_net_ids("L1") == frozenset({100})

    def test_multiple_shared_nets(self):
        store = ConflictStore()
        store.update_line("L1", {100, 200})
        store.update_line("L2", {100, 200})

        assert store.get_conflicting_net_ids("L1") == frozenset({100, 200})

    def test_conflict_info(self):
        store = ConflictStore()
        store.update_line("L1", {100, 200})
        store.update_line("L2", {100})

        info = store.get_conflict_info("L1")
        assert info is not None
        assert isinstance(info, ConflictInfo)
        assert info.conflicting_line_ids == {"L2"}
        assert info.shared_net_ids == frozenset({100})


class TestConflictStoreIncremental:

    def test_update_resolves_conflict(self):
        store = ConflictStore()
        store.update_line("L1", {100})
        store.update_line("L2", {100})
        assert store.is_conflicting("L1")

        # L2 changes to a different net — conflict resolved
        store.update_line("L2", {300})
        assert not store.is_conflicting("L1")
        assert not store.is_conflicting("L2")

    def test_update_creates_conflict(self):
        store = ConflictStore()
        store.update_line("L1", {100})
        store.update_line("L2", {300})
        assert not store.is_conflicting("L1")

        # L2 now covers 100 too
        store.update_line("L2", {100})
        assert store.is_conflicting("L1")
        assert store.is_conflicting("L2")

    def test_update_with_empty_removes_from_index(self):
        store = ConflictStore()
        store.update_line("L1", {100})
        store.update_line("L2", {100})
        assert store.is_conflicting("L1")

        store.update_line("L2", set())
        assert not store.is_conflicting("L1")

    def test_remove_line(self):
        store = ConflictStore()
        store.update_line("L1", {100})
        store.update_line("L2", {100})
        assert store.is_conflicting("L1")

        store.remove_line("L2")
        assert not store.is_conflicting("L1")
        assert store.get_conflict_info("L2") is None

    def test_remove_nonexistent_is_safe(self):
        store = ConflictStore()
        store.remove_line("nonexistent")  # no error

    def test_clear(self):
        store = ConflictStore()
        store.update_line("L1", {100})
        store.update_line("L2", {100})
        store.clear()
        assert not store.is_conflicting("L1")
        assert not store.is_conflicting("L2")


# ===========================================================
# resolve_line_nets
# ===========================================================

class TestResolveLineNets:

    def test_af_line_resolves_to_canonical_ids(self):
        nqs = MockNetlistQueryService()
        nqs.canonical_id_map[(None, "vdd", False)] = frozenset({10})

        data = AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)
        ids = resolve_line_nets(data, nqs)

        assert ids == frozenset({10})

    def test_af_line_with_template(self):
        nqs = MockNetlistQueryService()
        nqs.canonical_id_map[("t1", "vdd", False)] = frozenset({10, 20})

        data = AfLineData(template="t1", net="vdd", af_value=0.5, is_em_enabled=True)
        ids = resolve_line_nets(data, nqs)

        assert ids == frozenset({10, 20})

    def test_af_line_no_matches(self):
        nqs = MockNetlistQueryService()

        data = AfLineData(net="nonexistent", af_value=0.5, is_em_enabled=True)
        ids = resolve_line_nets(data, nqs)

        assert ids == frozenset()

    def test_mutex_line_resolves_to_canonical_ids(self):
        nqs = MockNetlistQueryService()
        nqs.canonical_id_map[(None, "vdd", False)] = frozenset({10})
        nqs.canonical_id_map[(None, "vss", False)] = frozenset({20})

        data = MutexLineData(
            num_active=1,
            mutexed_nets=["vdd", "vss"],
        )
        ids = resolve_line_nets(data, nqs)

        assert ids == frozenset({10, 20})

    def test_mutex_regex_line(self):
        nqs = MockNetlistQueryService()
        nqs.canonical_id_map[(None, "vdd.*", True)] = frozenset({10, 20})

        data = MutexLineData(
            num_active=1,
            is_regexp=True,
            mutexed_nets=["vdd.*"],
        )
        ids = resolve_line_nets(data, nqs)

        assert ids == frozenset({10, 20})
