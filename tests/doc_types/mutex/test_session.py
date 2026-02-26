import pytest

from doc_types.mutex import MutexEntry, FEVMode, MutexEditSessionState
from doc_types.mutex.exceptions import *


# ---------------------------
# Helper factory
# ---------------------------

def make_entry(net: str, template: str = "T1", regex=False, matches=None):
    return MutexEntry(
        net_name=net,
        template_name=template,
        regex_mode=regex,
        matches=matches if matches is not None else {net},
    )


# ===========================================================
# Basic add/remove
# ===========================================================

class TestAddMutexed:

    def test_add_mutexed_basic(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1")
        session.add_mutexed(e1)
        assert e1 in session.mutexed_entries
        assert session.template == "T1"
        assert session.regex_mode is False

    def test_add_duplicate_mutexed_raises(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1")
        session.add_mutexed(e1)
        with pytest.raises(DuplicateEntryError):
            session.add_mutexed(e1)

    def test_add_mutexed_with_no_matches_raises(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1", matches=set())
        with pytest.raises(NoMatchesError):
            session.add_mutexed(e1)


class TestAddActive:

    def test_add_active_basic(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1")
        session.add_active(e1)
        assert e1 in session.mutexed_entries
        assert e1 in session.active_entries

    def test_add_active_also_adds_mutexed(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1")
        session.add_active(e1)
        assert e1 in session.mutexed_entries

    def test_add_duplicate_active_raises(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1")
        session.add_active(e1)
        with pytest.raises(DuplicateEntryError):
            session.add_active(e1)

    def test_add_active_with_no_matches_raises(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1", matches=set())
        with pytest.raises(NoMatchesError):
            session.add_active(e1)

    def test_add_active_with_multiple_matches_raises(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1", matches={"net1", "net11"})
        with pytest.raises(ActiveMultipleMatchesError):
            session.add_active(e1)

    def test_active_cannot_be_regex(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1", regex=True)
        with pytest.raises(ActiveRegexError):
            session.add_active(e1)

    def test_add_active_when_net_covered_by_regex_mutexed(self):
        """Active net covered by a regex mutexed entry — no new mutexed entry needed."""
        session = MutexEditSessionState("s1")
        regex_entry = make_entry("g1.*", regex=True, matches={"g1.n1", "g1.n2", "g1.n3"})
        session.add_mutexed(regex_entry)
        active_entry = make_entry("g1.n1", matches={"g1.n1"})
        session.add_active(active_entry)
        assert active_entry in session.active_entries
        # Should NOT have been added as a separate mutexed entry
        assert len(session.mutexed_entries) == 1

    def test_add_active_uncovered_net_in_regex_session_raises(self):
        """Net not covered by any regex pattern — should give a clear error."""
        session = MutexEditSessionState("s1")
        regex_entry = make_entry("g1.*", regex=True, matches={"g1.n1", "g1.n2"})
        session.add_mutexed(regex_entry)
        uncovered = make_entry("other.net", matches={"other.net"})
        with pytest.raises(EntryNotFoundError, match="not covered"):
            session.add_active(uncovered)

    def test_add_active_idempotent_exact_session(self):
        """Net already in mutexed (exact) — just adds to active, no duplicate."""
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1")
        session.add_mutexed(e1)
        session.add_active(e1)
        assert e1 in session.active_entries
        assert len(session.mutexed_entries) == 1


# ===========================================================
# Template consistency
# ===========================================================

class TestTemplateConsistency:

    def test_template_mismatch_raises(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1", template="T1")
        e2 = make_entry("net2", template="T2")
        session.add_mutexed(e1)
        with pytest.raises(TemplateMismatchError):
            session.add_mutexed(e2)


# ===========================================================
# Regex mode consistency
# ===========================================================

class TestRegexConsistency:

    def test_regex_mismatch_raises(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1", regex=False)
        e2 = make_entry("net2", regex=True)
        session.add_mutexed(e1)
        with pytest.raises(RegexModeMismatchError):
            session.add_mutexed(e2)


# ===========================================================
# Intersection
# ===========================================================

class TestIntersection:

    def test_intersecting_mutexed_raises(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1", matches={"net1", "net2"})
        e2 = make_entry("net2", matches={"net2", "net3"})
        session.add_mutexed(e1)
        with pytest.raises(IntersectionError):
            session.add_mutexed(e2)

    def test_active_covered_by_mutexed_does_not_raise(self):
        """Adding an active entry whose net is covered by an existing
        mutexed pattern should succeed without adding a duplicate mutexed entry."""
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1", matches={"net1", "net2"})
        e2 = make_entry("net2", matches={"net2"})
        session.add_mutexed(e1)
        session.add_active(e2)
        assert e2 in session.active_entries
        # e2 should NOT have been added as a separate mutexed entry
        assert len(session.mutexed_entries) == 1


# ===========================================================
# Remove
# ===========================================================

class TestRemove:

    def test_remove_mutexed(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1", matches={"net1", "net11"})
        e2 = make_entry("net2", matches={"net2"})
        session.add_mutexed(e1)
        session.add_active(e2)
        session.remove_mutexed(e1)
        assert e1 not in session.mutexed_entries
        assert e2 in session.active_entries
        assert e2 in session.mutexed_entries

    def test_remove_active(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1")
        session.add_active(e1)
        session.remove_active(e1)
        assert e1 not in session.active_entries
        assert e1 in session.mutexed_entries

    def test_remove_mutexed_also_removes_intersecting_active(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1")
        session.add_active(e1)
        session.remove_mutexed(e1)
        assert e1 not in session.mutexed_entries
        assert e1 not in session.active_entries

    def test_remove_mutexed_nonexistent_raises(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1")
        with pytest.raises(EntryNotFoundError):
            session.remove_mutexed(e1)

    def test_remove_active_nonexistent_raises(self):
        session = MutexEditSessionState("s1")
        e1 = make_entry("net1")
        with pytest.raises(EntryNotFoundError):
            session.remove_active(e1)


# ===========================================================
# Empty session
# ===========================================================

class TestEmptySession:

    def test_empty_session_returns_none(self):
        session = MutexEditSessionState("s1")
        assert session.template is None
        assert session.regex_mode is None


# ===========================================================
# FEV mode
# ===========================================================

class TestFEVMode:

    def test_default_fev_is_empty(self):
        session = MutexEditSessionState("s1")
        assert session.fev == FEVMode.EMPTY

    def test_set_fev_low(self):
        session = MutexEditSessionState("s1")
        session.fev = FEVMode.LOW
        assert session.fev == FEVMode.LOW

    def test_set_fev_high(self):
        session = MutexEditSessionState("s1")
        session.fev = FEVMode.HIGH
        assert session.fev == FEVMode.HIGH

    def test_set_fev_ignore(self):
        session = MutexEditSessionState("s1")
        session.fev = FEVMode.IGNORE
        assert session.fev == FEVMode.IGNORE

    def test_set_fev_invalid_raises(self):
        session = MutexEditSessionState("s1")
        with pytest.raises(InvalidFEVModeError):
            session.fev = "bad_value"

    def test_set_fev_back_to_empty(self):
        session = MutexEditSessionState("s1")
        session.fev = FEVMode.HIGH
        session.fev = FEVMode.EMPTY
        assert session.fev == FEVMode.EMPTY


# ===========================================================
# num_active
# ===========================================================

class TestNumActive:

    def test_default_num_active(self):
        session = MutexEditSessionState("s1")
        assert session.num_active == 1

    def test_num_active_derived_from_active_entries(self):
        session = MutexEditSessionState("s1")
        session.add_active(make_entry("net1"))
        session.add_active(make_entry("net2"))
        assert session.num_active == 2

    def test_num_active_explicit_when_no_active_entries(self):
        session = MutexEditSessionState("s1")
        session.add_mutexed(make_entry("net1"))
        session.add_mutexed(make_entry("net2"))
        session.add_mutexed(make_entry("net3"))
        session.num_active = 2
        assert session.num_active == 2

    def test_set_num_active_with_active_entries_raises(self):
        session = MutexEditSessionState("s1")
        session.add_active(make_entry("net1"))
        with pytest.raises(ValueError, match="Cannot set num_active"):
            session.num_active = 2

    def test_set_num_active_negative_raises(self):
        session = MutexEditSessionState("s1")
        with pytest.raises(ValueError, match="cannot be negative"):
            session.num_active = -1

    def test_set_num_active_exceeds_mutexed_caught_by_validate(self):
        """Setting num_active >= mutexed count is allowed by setter,
        but caught by validate()."""
        session = MutexEditSessionState("s1")
        session.add_mutexed(make_entry("net1"))
        session.add_mutexed(make_entry("net2"))
        session.num_active = 2  # setter accepts it
        assert session.num_active == 2
        result = session.validate()
        assert not result
        assert any("must be less than" in e for e in result.errors)

    def test_set_num_active_on_empty_session(self):
        """num_active=0 is fine on an empty session (no mutexed nets to violate)."""
        session = MutexEditSessionState("s1")
        session.num_active = 0
        assert session.num_active == 0


# ===========================================================
# Validate
# ===========================================================

class TestValidate:

    def test_empty_session_is_invalid(self):
        session = MutexEditSessionState("s1")
        result = session.validate()
        assert not result
        assert len(result.errors) == 1

    def test_single_net_is_invalid(self):
        session = MutexEditSessionState("s1")
        session.add_mutexed(make_entry("net1"))
        result = session.validate()
        assert not result

    def test_two_nets_is_valid(self):
        session = MutexEditSessionState("s1")
        session.add_mutexed(make_entry("net1"))
        session.add_mutexed(make_entry("net2"))
        result = session.validate()
        assert result

    def test_active_count_must_be_less_than_mutexed(self):
        session = MutexEditSessionState("s1")
        session.add_active(make_entry("net1"))
        session.add_active(make_entry("net2"))
        result = session.validate()
        assert not result

    def test_valid_session(self):
        session = MutexEditSessionState("s1")
        session.add_mutexed(make_entry("net1"))
        session.add_mutexed(make_entry("net2"))
        session.add_active(make_entry("net3"))
        result = session.validate()
        assert result
        assert result.errors == []
