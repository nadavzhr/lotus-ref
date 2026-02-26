import pytest

from doc_types.mutex import MutexLineData, FEVMode, parser as mutex_parser
# ===========================================================
# is_comment / is_empty
# ===========================================================

class TestMutexParserTrivial:

    def test_comment(self):
        assert mutex_parser.is_comment("# mutex comment")

    def test_not_comment(self):
        assert not mutex_parser.is_comment("mutex2 regular net1 net2")

    def test_empty(self):
        assert mutex_parser.is_empty("")
        assert mutex_parser.is_empty("   ")


# ===========================================================
# Successful parsing
# ===========================================================

class TestMutexParserSuccess:

    def test_simple_regular(self):
        data = mutex_parser.parse("mutex2 regular net1 net2")
        assert data.num_active == 2
        assert data.fev == FEVMode.EMPTY
        assert data.is_regexp is False
        assert data.template is None
        assert data.mutexed_nets == ["net1", "net2"]
        assert data.active_nets == []

    def test_with_fev_suffix(self):
        data = mutex_parser.parse("mutex2_low regular net1 net2")
        assert data.fev == FEVMode.LOW

    def test_fev_high(self):
        data = mutex_parser.parse("mutex3_high regular net1 net2 net3")
        assert data.fev == FEVMode.HIGH

    def test_regexp_mode(self):
        data = mutex_parser.parse("mutex2 regexp vdd.* vss.*")
        assert data.is_regexp is True
        assert data.mutexed_nets == ["vdd.*", "vss.*"]

    def test_template_mode(self):
        data = mutex_parser.parse("mutex2 template T1 net1 net2")
        assert data.template == "T1"
        assert data.mutexed_nets == ["net1", "net2"]

    def test_active_nets(self):
        data = mutex_parser.parse("mutex2 regular net1 net2 on=net1")
        assert data.active_nets == ["net1"]

    def test_multiple_active_nets(self):
        data = mutex_parser.parse("mutex3 regular net1 net2 net3 on=net1,net2,net3")
        assert data.active_nets == ["net1", "net2", "net3"]

    def test_many_mutexed(self):
        data = mutex_parser.parse("mutex5 regular a b c d e")
        assert data.num_active == 5
        assert len(data.mutexed_nets) == 5


# ===========================================================
# Parse errors
# ===========================================================

class TestMutexParserErrors:

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="does not match"):
            mutex_parser.parse("not a mutex line")

    def test_missing_nets(self):
        with pytest.raises(ValueError, match="does not match"):
            mutex_parser.parse("mutex2 regular")
