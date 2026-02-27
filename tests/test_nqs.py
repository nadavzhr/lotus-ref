"""Tests for NetlistQueryService backed by netlist_parser."""
import os
import logging
import pytest

from nqs.netlist_query_service import NetlistQueryService
from nqs.netlist_parser.NetlistBuilder import NetlistBuilder

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "spice")
_SPICE_FILE = os.path.join(_DATA_DIR, "mycell.sp")


# ==================================================================
# Fixtures
# ==================================================================

@pytest.fixture
def nqs():
    builder = NetlistBuilder(logger=logging.getLogger("test"))
    svc = NetlistQueryService(cell="mycell", spice_file=_SPICE_FILE, netlist=builder)
    yield svc
    svc.close()


# ==================================================================
# Template queries
# ==================================================================

class TestTemplates:
    def test_top_cell(self, nqs):
        assert nqs.get_top_cell() == "mycell"

    def test_all_templates(self, nqs):
        assert nqs.get_all_templates() == {"a", "b", "c", "d", "mycell"}

    def test_template_exists(self, nqs):
        assert nqs.template_exists("d")
        assert nqs.template_exists("D")  # case insensitive
        assert not nqs.template_exists("nonexistent")

    def test_matching_templates_exact(self, nqs):
        assert nqs.get_matching_templates("d", is_regex=False) == {"d"}
        assert nqs.get_matching_templates("x", is_regex=False) == set()

    def test_matching_templates_regex(self, nqs):
        matches = nqs.get_matching_templates("^[a-d]$", is_regex=True)
        assert matches == {"a", "b", "c", "d"}


# ==================================================================
# Net queries
# ==================================================================

class TestNets:
    def test_nets_in_leaf_template(self, nqs):
        nets = nqs.get_all_nets_in_template("d")
        assert nets == {"n3", "m3", "o3", "vcc", "vss", "gd1", "gd2"}

    def test_nets_in_top_cell(self, nqs):
        nets = nqs.get_all_nets_in_template("mycell")
        for p in ("in1", "in2", "out1", "out2", "out3", "out4", "vcc", "vss"):
            assert p in nets

    def test_net_exists(self, nqs):
        assert nqs.net_exists("in1")
        assert nqs.net_exists("gd1", "d")
        assert not nqs.net_exists("in1", "d")


# ==================================================================
# Canonical name resolution
# ==================================================================

class TestCanonicalNames:
    def test_port_is_canonical(self, nqs):
        assert nqs.get_canonical_net_name("in1") == "in1"

    def test_instance_path_resolves_to_port(self, nqs):
        assert nqs.get_canonical_net_name("ia1/n0") == "in1"
        assert nqs.get_canonical_net_name("ia1/oa2") == "out2"

    def test_deep_hierarchy_resolves(self, nqs):
        assert nqs.get_canonical_net_name("ia1/ib/n1") == "in1"
        assert nqs.get_canonical_net_name("ia1/ib/ic/id1/n3") == "in1"

    def test_nonexistent_net_returns_none(self, nqs):
        assert nqs.get_canonical_net_name("doesnotexist") is None
        assert nqs.get_canonical_net_name("doesnotexist", "d") is None


# ==================================================================
# find_matches
# ==================================================================

class TestFindMatches:
    def test_exact_match_top_cell(self, nqs):
        nets, tpls = nqs.find_matches(None, "in1", False, False)
        assert "in1" in nets
        assert "mycell" in tpls

    def test_exact_match_template(self, nqs):
        nets, tpls = nqs.find_matches("d", "gd1", False, False)
        assert nets == ["d:gd1"]
        assert tpls == ["d"]

    def test_regex_match(self, nqs):
        nets, tpls = nqs.find_matches("d", "gd.*", False, True)
        assert "d:gd1" in nets
        assert "d:gd2" in nets

    def test_alias_resolution_in_find_matches(self, nqs):
        nets, tpls = nqs.find_matches(None, "ia1/ib/n1", False, False)
        assert "in1" in nets

    def test_no_matches(self, nqs):
        nets, tpls = nqs.find_matches("d", "doesnotexist", False, False)
        assert nets == []
        assert tpls == []


# ==================================================================
# find_net_instance_names
# ==================================================================

class TestFindNetInstanceNames:
    """Test find_net_instance_names — delegates to netlist_parser."""

    def test_top_cell_net_returns_itself(self, nqs):
        names = nqs.find_net_instance_names("mycell", "in1")
        assert "in1" in names

    def test_template_port_resolves_through_hierarchy(self, nqs):
        names = nqs.find_net_instance_names("d", "n3")
        assert len(names) > 0
        assert "in1" in names or any("n3" in n for n in names)

    def test_nonexistent_template_returns_empty(self, nqs):
        names = nqs.find_net_instance_names("nosuch", "n1")
        assert names == set()

    def test_nonexistent_net_returns_empty(self, nqs):
        names = nqs.find_net_instance_names("d", "nonexistent")
        assert names == set()


# ==================================================================
# Static helpers
# ==================================================================

class TestStaticHelpers:
    def test_normalize_net_for_template(self):
        assert NetlistQueryService.normalize_net_for_template("d:gd1", "d") == "gd1"
        assert NetlistQueryService.normalize_net_for_template("gd1", "d") == "gd1"

    def test_has_bus_notation(self):
        assert NetlistQueryService.has_bus_notation("net[0:3]")
        assert not NetlistQueryService.has_bus_notation("net")

    def test_expand_bus_notation(self):
        result = NetlistQueryService.expand_bus_notation("net[0:2]")
        assert result == ["net[0]", "net[1]", "net[2]"]


# ==================================================================
# Lifecycle
# ==================================================================

class TestLifecycle:
    def test_context_manager(self):
        builder = NetlistBuilder(logger=logging.getLogger("test"))
        with NetlistQueryService(cell="mycell", spice_file=_SPICE_FILE, netlist=builder) as svc:
            assert svc.get_top_cell() == "mycell"

    def test_file_not_found(self):
        builder = NetlistBuilder(logger=logging.getLogger("test"))
        with pytest.raises(FileNotFoundError):
            NetlistQueryService(cell="mycell", spice_file="/nonexistent.sp", netlist=builder)

    def test_cell_not_found(self):
        builder = NetlistBuilder(logger=logging.getLogger("test"))
        with pytest.raises(RuntimeError):
            NetlistQueryService(cell="nosuchcell", spice_file=_SPICE_FILE, netlist=builder)


# ==================================================================
# ConflictDetector integration (real NQS + hierarchy)
# ==================================================================

from core.conflict_store import ConflictDetector


class TestConflictDetectorIntegration:
    """Verify ConflictDetector with the real NQS and hierarchy data."""

    def test_top_cell_net_resolves(self, nqs):
        det = ConflictDetector(nqs)
        ids = det.resolve_to_canonical_ids(None, "in1", False, False)
        assert len(ids) == 1
        nid = next(iter(ids))
        assert det.canonical_net_name(nid) == "in1"

    def test_alias_resolves_to_canonical(self, nqs):
        det = ConflictDetector(nqs)
        ids = det.resolve_to_canonical_ids(None, "ia1/ib/n1", False, False)
        assert len(ids) == 1
        nid = next(iter(ids))
        assert det.canonical_net_name(nid) == "in1"

    def test_template_net_resolves_through_hierarchy(self, nqs):
        det = ConflictDetector(nqs)
        ids = det.resolve_to_canonical_ids("d", "n3", False, False)
        assert len(ids) > 0
        id_names = {det.canonical_net_name(nid) for nid in ids}
        assert "in1" in id_names

    def test_hierarchical_conflict_d_n3_vs_c_n2(self, nqs):
        det = ConflictDetector(nqs)
        d_ids = det.resolve_to_canonical_ids("d", "n3", False, False)
        c_ids = det.resolve_to_canonical_ids("c", "n2", False, False)
        assert d_ids & c_ids, "d:n3 and c:n2 should share at least one top-cell net"

    def test_hierarchical_conflict_d_n3_vs_top_in1(self, nqs):
        det = ConflictDetector(nqs)
        d_ids = det.resolve_to_canonical_ids("d", "n3", False, False)
        top_ids = det.resolve_to_canonical_ids(None, "in1", False, False)
        assert d_ids & top_ids, "d:n3 should conflict with top-cell in1"

    def test_no_conflict_between_unrelated_nets(self, nqs):
        det = ConflictDetector(nqs)
        d_gd1_ids = det.resolve_to_canonical_ids("d", "gd1", False, False)
        in2_ids = det.resolve_to_canonical_ids(None, "in2", False, False)
        assert not (d_gd1_ids & in2_ids)

    def test_regex_resolves(self, nqs):
        det = ConflictDetector(nqs)
        ids = det.resolve_to_canonical_ids("d", "n.*", False, True)
        assert len(ids) > 0

    def test_empty_net_returns_empty(self, nqs):
        det = ConflictDetector(nqs)
        assert det.resolve_to_canonical_ids(None, "", False, False) == frozenset()

    def test_nonexistent_template_returns_empty(self, nqs):
        det = ConflictDetector(nqs)
        assert det.resolve_to_canonical_ids("nosuch", "n1", False, False) == frozenset()

    def test_nonexistent_net_returns_empty(self, nqs):
        det = ConflictDetector(nqs)
        assert det.resolve_to_canonical_ids("d", "nonexistent", False, False) == frozenset()

    def test_consistency_with_find_net_instance_names(self, nqs):
        """Integer IDs should map back to exactly the instance names."""
        det = ConflictDetector(nqs)
        names = nqs.find_net_instance_names("d", "n3")
        ids = det.resolve_to_canonical_ids("d", "n3", False, False)
        id_names = {det.canonical_net_name(nid) for nid in ids}
        assert id_names == names

    def test_hierarchy_cache_populated(self, nqs):
        """Verify the unbounded hierarchy cache is populated after resolution."""
        det = ConflictDetector(nqs)
        info_before = det._resolve_tpl_net_to_top_ids.cache_info()

        det.resolve_to_canonical_ids("d", "n3", False, False)
        info_after = det._resolve_tpl_net_to_top_ids.cache_info()
        assert info_after.currsize > info_before.currsize

    def test_repeated_calls_hit_cache(self, nqs):
        """Second call should hit the hierarchy cache."""
        det = ConflictDetector(nqs)
        det.resolve_to_canonical_ids("d", "n3", False, False)
        info1 = det._resolve_tpl_net_to_top_ids.cache_info()

        # Clear the outer resolve cache so it re-enters the method
        det.resolve_to_canonical_ids.cache_clear()
        det.resolve_to_canonical_ids("d", "n3", False, False)
        info2 = det._resolve_tpl_net_to_top_ids.cache_info()
        assert info2.hits > info1.hits
