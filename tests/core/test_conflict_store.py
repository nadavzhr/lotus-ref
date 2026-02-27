import pytest

from core.conflict_store import ConflictStore, ConflictInfo, ConflictDetector
from core.document_line import DocumentLine
from core.validation_result import ValidationResult
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
        store.update_line("L1", {"net100", "net200"})
        assert not store.is_conflicting("L1")
        assert store.get_conflicting_lines("L1") == set()
        assert store.get_conflicting_net_ids("L1") == frozenset()
        assert store.get_conflict_info("L1") is None


class TestConflictStoreDetection:

    def test_two_lines_same_net_conflict(self):
        store = ConflictStore()
        store.update_line("L1", {"net100", "net200"})
        store.update_line("L2", {"net100", "net300"})

        assert store.is_conflicting("L1")
        assert store.is_conflicting("L2")
        assert store.get_conflicting_lines("L1") == {"L2"}
        assert store.get_conflicting_lines("L2") == {"L1"}
        assert store.get_conflicting_net_ids("L1") == frozenset({"net100"})
        assert store.get_conflicting_net_ids("L2") == frozenset({"net100"})

    def test_no_overlap_no_conflict(self):
        store = ConflictStore()
        store.update_line("L1", {"net100"})
        store.update_line("L2", {"net200"})

        assert not store.is_conflicting("L1")
        assert not store.is_conflicting("L2")

    def test_three_lines_shared_net(self):
        store = ConflictStore()
        store.update_line("L1", {"net100"})
        store.update_line("L2", {"net100", "net300"})
        store.update_line("L3", {"net100"})

        assert store.is_conflicting("L1")
        assert store.get_conflicting_lines("L1") == {"L2", "L3"}
        assert store.get_conflicting_net_ids("L1") == frozenset({"net100"})

    def test_multiple_shared_nets(self):
        store = ConflictStore()
        store.update_line("L1", {"net100", "net200"})
        store.update_line("L2", {"net100", "net200"})

        assert store.get_conflicting_net_ids("L1") == frozenset({"net100", "net200"})

    def test_conflict_info(self):
        store = ConflictStore()
        store.update_line("L1", {"net100", "net200"})
        store.update_line("L2", {"net100"})

        info = store.get_conflict_info("L1")
        assert info is not None
        assert isinstance(info, ConflictInfo)
        assert info.conflicting_line_ids == {"L2"}
        assert info.shared_net_ids == frozenset({"net100"})


class TestConflictStoreUpdates:

    def test_update_resolves_conflict(self):
        store = ConflictStore()
        store.update_line("L1", {"net100"})
        store.update_line("L2", {"net100"})
        assert store.is_conflicting("L1")

        # L2 changes to a different net — conflict resolved
        store.update_line("L2", {"net300"})
        assert not store.is_conflicting("L1")
        assert not store.is_conflicting("L2")

    def test_update_creates_conflict(self):
        store = ConflictStore()
        store.update_line("L1", {"net100"})
        store.update_line("L2", {"net300"})
        assert not store.is_conflicting("L1")

        # L2 now covers 100 too
        store.update_line("L2", {"net100"})
        assert store.is_conflicting("L1")
        assert store.is_conflicting("L2")

    def test_update_with_empty_removes_from_index(self):
        store = ConflictStore()
        store.update_line("L1", {"net100"})
        store.update_line("L2", {"net100"})
        assert store.is_conflicting("L1")

        store.update_line("L2", set())
        assert not store.is_conflicting("L1")

    def test_remove_line(self):
        store = ConflictStore()
        store.update_line("L1", {"net100"})
        store.update_line("L2", {"net100"})
        assert store.is_conflicting("L1")

        store.remove_line("L2")
        assert not store.is_conflicting("L1")
        assert store.get_conflict_info("L2") is None

    def test_remove_nonexistent_is_safe(self):
        store = ConflictStore()
        store.remove_line("nonexistent")  # no error

    def test_clear(self):
        store = ConflictStore()
        store.update_line("L1", {"net100"})
        store.update_line("L2", {"net100"})
        store.clear()
        assert not store.is_conflicting("L1")
        assert not store.is_conflicting("L2")


# ===========================================================
# ConflictDetector
# ===========================================================

def _make_line(line_id: str, data=None) -> DocumentLine:
    """Helper to create a DocumentLine with optional data."""
    return DocumentLine(
        line_id=line_id,
        raw_text="",
        data=data,
        validation_result=ValidationResult(),
    )


def _make_mock_nqs_for_detector():
    """Create a mock NQS with enough data to support ConflictDetector."""
    nqs = MockNetlistQueryService()
    nqs.top_cell = "top"
    nqs.templates = {"top"}
    nqs.nets_in_template = {"top": {"vdd", "vss", "clk"}}
    # Canonical name lookups (fast path uses get_canonical_net_name)
    nqs.canonical_map = {
        ("vdd", "top"): "vdd",
        ("vss", "top"): "vss",
        ("clk", "top"): "clk",
    }
    # find_matches returns qualified net names (slow path / regex)
    nqs.net_matches = {
        (None, "vdd", False): ["vdd"],
        ("top", "vdd", False): ["vdd"],
        (None, "vss", False): ["vss"],
        ("top", "vss", False): ["vss"],
        (None, "clk", False): ["clk"],
        ("top", "clk", False): ["clk"],
    }
    # Hierarchy resolution: template-scoped net → top-cell names
    nqs.instance_names_map = {
        ("top", "vdd"): {"vdd"},
        ("top", "vss"): {"vss"},
        ("top", "clk"): {"clk"},
    }
    return nqs


class TestConflictDetectorResolve:

    def test_resolve_to_canonical_ids(self):
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        ids = det.resolve_to_canonical_names(None, "vdd", False, False)
        assert ids == frozenset({"vdd"})

    def test_empty_net_returns_empty(self):
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)
        assert det.resolve_to_canonical_names(None, "", False, False) == frozenset()

    def test_nonexistent_net_returns_empty(self):
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)
        assert det.resolve_to_canonical_names(None, "nonexistent", False, False) == frozenset()


class TestConflictDetectorRebuild:

    def test_rebuild_detects_conflict(self):
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", AfLineData(net="vdd", af_value=0.8, is_em_enabled=True)),
        ]
        det.rebuild(lines)

        assert det.is_conflicting("L1")
        assert det.is_conflicting("L2")
        assert det.get_conflicting_lines("L1") == {"L2"}

    def test_rebuild_no_conflict(self):
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", AfLineData(net="vss", af_value=0.5, is_em_enabled=True)),
        ]
        det.rebuild(lines)

        assert not det.is_conflicting("L1")
        assert not det.is_conflicting("L2")

    def test_rebuild_replaces_old_state(self):
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        # First: conflict
        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", AfLineData(net="vdd", af_value=0.8, is_em_enabled=True)),
        ]
        det.rebuild(lines)
        assert det.is_conflicting("L1")

        # Second: no conflict
        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", AfLineData(net="vss", af_value=0.5, is_em_enabled=True)),
        ]
        det.rebuild(lines)
        assert not det.is_conflicting("L1")
        assert not det.is_conflicting("L2")

    def test_rebuild_skips_comment_lines(self):
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", None),  # comment or blank
        ]
        det.rebuild(lines)
        assert not det.is_conflicting("L1")

    def test_conflict_info(self):
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", AfLineData(net="vdd", af_value=0.8, is_em_enabled=True)),
        ]
        det.rebuild(lines)

        info = det.get_conflict_info("L1")
        assert info is not None
        assert info.conflicting_line_ids == {"L2"}
        assert len(info.shared_net_ids) == 1

    def test_mutex_line_resolves(self):
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", MutexLineData(num_active=1, mutexed_nets=("vdd", "vss"))),
        ]
        det.rebuild(lines)
        # L1 covers vdd, L2 covers vdd+vss → overlap on vdd
        assert det.is_conflicting("L1")
        assert det.is_conflicting("L2")


# ===========================================================
# ConflictDetector — incremental updates
# ===========================================================

class TestConflictDetectorUpdateLine:
    """Tests for ConflictDetector.update_line() — the incremental edit path."""

    def test_update_creates_conflict(self):
        """Editing a line to overlap with another should create a conflict."""
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        # Initial state: no conflict (vdd vs vss)
        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", AfLineData(net="vss", af_value=0.5, is_em_enabled=True)),
        ]
        det.rebuild(lines)
        assert not det.is_conflicting("L1")
        assert not det.is_conflicting("L2")

        # Edit L2 to also cover vdd → conflict
        new_data = AfLineData(net="vdd", af_value=0.8, is_em_enabled=True)
        det.update_line("L2", new_data)

        assert det.is_conflicting("L1")
        assert det.is_conflicting("L2")
        assert det.get_conflicting_lines("L1") == {"L2"}
        assert det.get_conflicting_lines("L2") == {"L1"}

    def test_update_resolves_conflict(self):
        """Editing a line away from a shared net should resolve the conflict."""
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        # Initial state: conflict (both on vdd)
        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", AfLineData(net="vdd", af_value=0.8, is_em_enabled=True)),
        ]
        det.rebuild(lines)
        assert det.is_conflicting("L1")

        # Edit L2 to vss → conflict resolved
        new_data = AfLineData(net="vss", af_value=0.8, is_em_enabled=True)
        det.update_line("L2", new_data)

        assert not det.is_conflicting("L1")
        assert not det.is_conflicting("L2")

    def test_update_with_none_removes_from_conflicts(self):
        """Setting data to None (comment/blank) should remove from conflicts."""
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", AfLineData(net="vdd", af_value=0.8, is_em_enabled=True)),
        ]
        det.rebuild(lines)
        assert det.is_conflicting("L1")

        # L2 becomes a comment
        det.update_line("L2", None)

        assert not det.is_conflicting("L1")
        assert not det.is_conflicting("L2")

    def test_update_affects_all_peers(self):
        """When line X is edited, all peers' conflict status should update."""
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        # Three lines on vdd
        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", AfLineData(net="vdd", af_value=0.8, is_em_enabled=True)),
            _make_line("L3", AfLineData(net="vdd", af_value=0.3, is_em_enabled=True)),
        ]
        det.rebuild(lines)
        assert det.get_conflicting_lines("L1") == {"L2", "L3"}

        # Remove L3 from vdd
        det.update_line("L3", AfLineData(net="vss", af_value=0.3, is_em_enabled=True))

        # L1 and L2 still conflict with each other, but L3 is gone
        assert det.is_conflicting("L1")
        assert det.get_conflicting_lines("L1") == {"L2"}
        assert not det.is_conflicting("L3")

    def test_update_previously_no_conflict_creates_multi_conflict(self):
        """
        A single edit to a previously-non-conflicting line can create
        conflicts with many other lines simultaneously.
        """
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        # L1, L2, L3 all on vdd; L4 on vss (no conflict with L4)
        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", AfLineData(net="vdd", af_value=0.8, is_em_enabled=True)),
            _make_line("L3", AfLineData(net="vdd", af_value=0.3, is_em_enabled=True)),
            _make_line("L4", AfLineData(net="vss", af_value=0.5, is_em_enabled=True)),
        ]
        det.rebuild(lines)
        assert not det.is_conflicting("L4")

        # Edit L4 to vdd → now conflicts with L1, L2, L3
        det.update_line("L4", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True))

        assert det.is_conflicting("L4")
        assert det.get_conflicting_lines("L4") == {"L1", "L2", "L3"}
        # All original vdd lines should now also show L4 as a peer
        assert "L4" in det.get_conflicting_lines("L1")
        assert "L4" in det.get_conflicting_lines("L2")
        assert "L4" in det.get_conflicting_lines("L3")


class TestConflictDetectorRemoveLine:
    """Tests for ConflictDetector.remove_line() — the line deletion path."""

    def test_remove_resolves_conflict(self):
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", AfLineData(net="vdd", af_value=0.8, is_em_enabled=True)),
        ]
        det.rebuild(lines)
        assert det.is_conflicting("L1")

        det.remove_line("L2")

        assert not det.is_conflicting("L1")
        assert det.get_conflict_info("L2") is None

    def test_remove_nonexistent_is_safe(self):
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)
        det.remove_line("nonexistent")  # should not raise

    def test_remove_preserves_other_conflicts(self):
        """Removing one line from a 3-way conflict leaves the other two conflicting."""
        nqs = _make_mock_nqs_for_detector()
        det = ConflictDetector(nqs)

        lines = [
            _make_line("L1", AfLineData(net="vdd", af_value=0.5, is_em_enabled=True)),
            _make_line("L2", AfLineData(net="vdd", af_value=0.8, is_em_enabled=True)),
            _make_line("L3", AfLineData(net="vdd", af_value=0.3, is_em_enabled=True)),
        ]
        det.rebuild(lines)
        assert det.get_conflicting_lines("L1") == {"L2", "L3"}

        det.remove_line("L3")

        assert det.is_conflicting("L1")
        assert det.get_conflicting_lines("L1") == {"L2"}
        assert det.is_conflicting("L2")
        assert det.get_conflicting_lines("L2") == {"L1"}
