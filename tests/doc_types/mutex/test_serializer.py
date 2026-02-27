import pytest

from doc_types.mutex import MutexLineData, FEVMode, serializer as mutex_serializer, parser as mutex_parser
# ===========================================================
# Serialization
# ===========================================================

class TestMutexSerializer:

    def test_simple_regular(self):
        data = MutexLineData(num_active=2, mutexed_nets=("net1", "net2"))
        result = mutex_serializer.serialize(data)
        assert result == "mutex2 regular net1 net2"

    def test_with_fev_suffix(self):
        data = MutexLineData(num_active=2, fev=FEVMode.LOW, mutexed_nets=("net1", "net2"))
        result = mutex_serializer.serialize(data)
        assert result == "mutex2_low regular net1 net2"

    def test_regexp_mode(self):
        data = MutexLineData(num_active=2, is_net_regex=True, mutexed_nets=("vdd.*", "vss.*"))
        result = mutex_serializer.serialize(data)
        assert result == "mutex2 regexp vdd.* vss.*"

    def test_template_mode(self):
        data = MutexLineData(
            num_active=2, template="T1", mutexed_nets=("net1", "net2"),
        )
        result = mutex_serializer.serialize(data)
        assert result == "mutex2 template T1 net1 net2"

    def test_with_active_nets(self):
        data = MutexLineData(
            num_active=2, mutexed_nets=("net1", "net2"), active_nets=("net1",),
        )
        result = mutex_serializer.serialize(data)
        assert result == "mutex2 regular net1 net2 on=net1"

    def test_multiple_active(self):
        data = MutexLineData(
            num_active=3, mutexed_nets=("a", "b", "c"), active_nets=("a", "b", "c"),
        )
        result = mutex_serializer.serialize(data)
        assert "on=a,b,c" in result


# ===========================================================
# Round-trip: parse → serialize → parse
# ===========================================================

class TestMutexRoundTrip:

    @pytest.mark.parametrize("line", [
        "mutex2_low regular net1 net2",
        "mutex3_high regular net1 net2 net3",
        "mutex2_ignore regexp vdd.* vss.*",
        "mutex2_high template T1 net1 net2",
        "mutex2_low regular net1 net2 on=net1",
    ])
    def test_round_trip(self, line):
        data = mutex_parser.parse(line)
        serialized = mutex_serializer.serialize(data)
        reparsed = mutex_parser.parse(serialized)
        assert data == reparsed
