"""Tests for SpiceNetlistQueryService — the SPICE-file-backed NQS clone."""
import os
import pytest

from nqs.spice_nqs import SpiceNetlistQueryService, parse_spice_file

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "spice")
_SPICE_FILE = os.path.join(_DATA_DIR, "mycell.sp")


# ==================================================================
# Fixtures
# ==================================================================

@pytest.fixture
def nqs():
    svc = SpiceNetlistQueryService(cell="mycell", spice_file=_SPICE_FILE)
    yield svc
    svc.close()


# ==================================================================
# SPICE parser
# ==================================================================

class TestSpiceParser:
    def test_parse_templates(self):
        subckts = parse_spice_file(_SPICE_FILE)
        assert set(subckts.keys()) == {"d", "c", "b", "a", "mycell"}

    def test_parse_ports(self):
        subckts = parse_spice_file(_SPICE_FILE)
        assert subckts["d"].ports == ["n3", "m3", "o3", "vcc", "vss"]
        assert subckts["mycell"].ports == [
            "in1", "in2", "out1", "out2", "out3", "out4", "vcc", "vss",
        ]

    def test_parse_instances(self):
        subckts = parse_spice_file(_SPICE_FILE)
        assert len(subckts["mycell"].instances) == 2
        inst = subckts["mycell"].instances[0]
        assert inst.inst_name == "ia1"
        assert inst.subckt_name == "a"

    def test_parse_local_nets(self):
        subckts = parse_spice_file(_SPICE_FILE)
        assert "gd1" in subckts["d"].local_nets
        assert "gd2" in subckts["d"].local_nets
        assert "nonpinb" in subckts["b"].local_nets


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

    def test_nets_in_mid_template(self, nqs):
        nets = nqs.get_all_nets_in_template("b")
        expected = {
            "n1", "o1", "xo1", "vcc", "vss", "nonpinb",
            "ic/dummy_o",
            "ic/id1/gd1", "ic/id1/gd2",
            "ic/id2/gd1", "ic/id2/gd2",
        }
        assert nets == expected

    def test_nets_in_top_cell(self, nqs):
        nets = nqs.get_all_nets_in_template("mycell")
        # Ports
        for p in ("in1", "in2", "out1", "out2", "out3", "out4", "vcc", "vss"):
            assert p in nets
        # Internal nets
        assert "ia1/ib/nonpinb" in nets
        assert "ia2/ib/nonpinb" in nets
        assert "ia1/ib/ic/id1/gd1" in nets

    def test_net_exists(self, nqs):
        assert nqs.net_exists("in1")
        assert nqs.net_exists("gd1", "d")
        assert not nqs.net_exists("in1", "d")

    def test_net_exists_alias(self, nqs):
        # ia1/n0 is an alias for in1 in mycell
        assert nqs.net_exists("ia1/n0")


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

    def test_internal_net_stays_canonical(self, nqs):
        assert nqs.get_canonical_net_name("ia1/ib/nonpinb") == "ia1/ib/nonpinb"
        assert nqs.get_canonical_net_name("ia1/ib/ic/id1/gd1") == "ia1/ib/ic/id1/gd1"

    def test_template_scoped_canonical(self, nqs):
        assert nqs.get_canonical_net_name("nonpinb", "b") == "nonpinb"
        assert nqs.get_canonical_net_name("ic/m2", "b") == "nonpinb"

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
# Static helpers
# ==================================================================

class TestStaticHelpers:
    def test_normalize_net_for_template(self):
        assert SpiceNetlistQueryService.normalize_net_for_template(
            "d:gd1", "d"
        ) == "gd1"
        assert SpiceNetlistQueryService.normalize_net_for_template(
            "gd1", "d"
        ) == "gd1"

    def test_has_bus_notation(self):
        assert SpiceNetlistQueryService.has_bus_notation("net[0:3]")
        assert not SpiceNetlistQueryService.has_bus_notation("net")

    def test_expand_bus_notation(self):
        result = SpiceNetlistQueryService.expand_bus_notation("net[0:2]")
        assert result == ["net[0]", "net[1]", "net[2]"]


# ==================================================================
# Lifecycle
# ==================================================================

class TestLifecycle:
    def test_context_manager(self):
        with SpiceNetlistQueryService(
            cell="mycell", spice_file=_SPICE_FILE
        ) as svc:
            assert svc.get_top_cell() == "mycell"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            SpiceNetlistQueryService(cell="mycell", spice_file="/nonexistent.sp")

    def test_cell_not_found(self):
        with pytest.raises(RuntimeError, match="not found"):
            SpiceNetlistQueryService(cell="nosuchcell", spice_file=_SPICE_FILE)


# ==================================================================
# Canonical net ID resolution
# ==================================================================

class TestCanonicalIdTable:
    """Verify the canonical ID infrastructure is built correctly."""

    def test_net_id_map_covers_all_top_cell_nets(self, nqs):
        """Every top-cell canonical net should have an integer ID."""
        top_canonical = nqs._canonical_nets[nqs._top_cell]
        assert len(nqs._net_id_map) == len(top_canonical)
        for name in top_canonical:
            assert name in nqs._net_id_map

    def test_id_net_map_is_inverse(self, nqs):
        """id_net_map should be the exact inverse of net_id_map."""
        for name, nid in nqs._net_id_map.items():
            assert nqs._id_net_map[nid] == name
        for nid, name in nqs._id_net_map.items():
            assert nqs._net_id_map[name] == nid

    def test_canonical_net_name_method(self, nqs):
        """canonical_net_name() returns the name for a known ID."""
        nid = nqs._net_id_map["in1"]
        assert nqs.canonical_net_name(nid) == "in1"

    def test_canonical_net_name_unknown(self, nqs):
        assert nqs.canonical_net_name(-1) is None


class TestInstancePaths:
    """Verify _template_instances is built correctly."""

    def test_leaf_template_has_instances(self, nqs):
        """D is instantiated 4 times (2 per C × 2 C instances)."""
        paths = nqs._template_instances.get("d", [])
        assert len(paths) == 4
        assert "ia1/ib/ic/id1" in paths
        assert "ia1/ib/ic/id2" in paths
        assert "ia2/ib/ic/id1" in paths
        assert "ia2/ib/ic/id2" in paths

    def test_mid_template_has_instances(self, nqs):
        paths = nqs._template_instances.get("c", [])
        assert len(paths) == 2
        assert "ia1/ib/ic" in paths
        assert "ia2/ib/ic" in paths

    def test_top_cell_has_no_instances(self, nqs):
        paths = nqs._template_instances.get("mycell", [])
        assert len(paths) == 0


class TestResolveToCanonicalIds:
    """Test the core resolve_to_canonical_ids method."""

    def test_top_cell_net_resolves(self, nqs):
        """A direct top-cell net like 'in1' should resolve to exactly one ID."""
        ids = nqs.resolve_to_canonical_ids(None, "in1", False, False)
        assert len(ids) == 1
        nid = next(iter(ids))
        assert nqs.canonical_net_name(nid) == "in1"

    def test_alias_resolves_to_canonical(self, nqs):
        """Hierarchical alias 'ia1/ib/n1' should resolve to 'in1'."""
        ids = nqs.resolve_to_canonical_ids(None, "ia1/ib/n1", False, False)
        assert len(ids) == 1
        nid = next(iter(ids))
        assert nqs.canonical_net_name(nid) == "in1"

    def test_template_net_resolves_through_hierarchy(self, nqs):
        """
        {D:n3} should resolve to multiple top-cell canonical nets because
        D is instantiated 4 times. n3 is a port of D.
        """
        ids = nqs.resolve_to_canonical_ids("d", "n3", False, False)
        assert len(ids) > 0
        # n3 in D at ia1/ib/ic/id1 connects to C:n2, B:n1, A:n0, mycell:in1
        in1_id = nqs._net_id_map["in1"]
        assert in1_id in ids

    def test_hierarchical_conflict_d_n3_vs_c_n2(self, nqs):
        """
        {D:n3} and {C:n2} must share at least one canonical net ID.
        This is the fundamental hierarchical conflict scenario.
        """
        d_ids = nqs.resolve_to_canonical_ids("d", "n3", False, False)
        c_ids = nqs.resolve_to_canonical_ids("c", "n2", False, False)
        overlap = d_ids & c_ids
        assert len(overlap) > 0, (
            f"D:n3 and C:n2 should share canonical nets but don't.\n"
            f"D:n3 IDs: {sorted(d_ids)}\n"
            f"C:n2 IDs: {sorted(c_ids)}"
        )

    def test_hierarchical_conflict_d_n3_vs_b_n1(self, nqs):
        """{D:n3} and {B:n1} must share canonical nets (through hierarchy)."""
        d_ids = nqs.resolve_to_canonical_ids("d", "n3", False, False)
        b_ids = nqs.resolve_to_canonical_ids("b", "n1", False, False)
        overlap = d_ids & b_ids
        assert len(overlap) > 0

    def test_hierarchical_conflict_c_n2_vs_b_n1(self, nqs):
        """{C:n2} and {B:n1} must share canonical nets."""
        c_ids = nqs.resolve_to_canonical_ids("c", "n2", False, False)
        b_ids = nqs.resolve_to_canonical_ids("b", "n1", False, False)
        overlap = c_ids & b_ids
        assert len(overlap) > 0

    def test_hierarchical_conflict_d_n3_vs_top_in1(self, nqs):
        """
        {D:n3} should conflict with top-cell {in1} — the
        template-scoped net resolves through the hierarchy to the same
        physical net.
        """
        d_ids = nqs.resolve_to_canonical_ids("d", "n3", False, False)
        top_ids = nqs.resolve_to_canonical_ids(None, "in1", False, False)
        overlap = d_ids & top_ids
        assert len(overlap) > 0

    def test_no_conflict_between_unrelated_nets(self, nqs):
        """Internal net d:gd1 should not overlap with top-cell in2."""
        d_gd1_ids = nqs.resolve_to_canonical_ids("d", "gd1", False, False)
        in2_ids = nqs.resolve_to_canonical_ids(None, "in2", False, False)
        overlap = d_gd1_ids & in2_ids
        assert len(overlap) == 0

    def test_regex_resolves(self, nqs):
        """Regex pattern should resolve through hierarchy."""
        ids = nqs.resolve_to_canonical_ids("d", "n.*", False, True)
        assert len(ids) > 0
        # Should include n3 resolutions
        in1_id = nqs._net_id_map["in1"]
        assert in1_id in ids

    def test_empty_net_returns_empty(self, nqs):
        assert nqs.resolve_to_canonical_ids(None, "", False, False) == frozenset()

    def test_nonexistent_template_returns_empty(self, nqs):
        assert nqs.resolve_to_canonical_ids("nosuch", "n1", False, False) == frozenset()

    def test_nonexistent_net_returns_empty(self, nqs):
        assert nqs.resolve_to_canonical_ids("d", "nonexistent", False, False) == frozenset()
