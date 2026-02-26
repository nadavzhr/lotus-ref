import pytest

from doc_types.af import AfLineData, AfEditController
from tests.mock_nqs import MockNetlistQueryService


@pytest.fixture
def nqs():
    return MockNetlistQueryService()


@pytest.fixture
def ctrl(nqs):
    c = AfEditController(nqs)
    c.start_session("s1")
    return c


# ===========================================================
# Session lifecycle
# ===========================================================

class TestAfControllerSessionLifecycle:

    def test_fresh_controller_has_empty_session(self, nqs):
        c = AfEditController(nqs)
        assert c.session.net_name == ""

    def test_start_session_replaces_old(self, nqs):
        c = AfEditController(nqs)
        c.start_session("s1")
        c.set_net("vdd")
        c.start_session("s2")
        assert c.session.net_name == ""  # fresh session


# ===========================================================
# Mutation pass-through
# ===========================================================

class TestAfControllerMutation:

    def test_set_template(self, ctrl):
        ctrl.set_template("T1")
        ctrl.set_template_regex(True)
        assert ctrl.session.template_name == "T1"
        assert ctrl.session.template_regex_mode is True

    def test_set_net(self, ctrl):
        ctrl.set_net("vdd.*")
        ctrl.set_net_regex(True)
        assert ctrl.session.net_name == "vdd.*"
        assert ctrl.session.net_regex_mode is True

    def test_set_af_value(self, ctrl):
        ctrl.set_af_value(0.75)
        assert ctrl.session.af_value == 0.75

    def test_set_mode(self, ctrl):
        ctrl.set_em_mode(True)
        ctrl.set_sh_mode(False)
        assert ctrl.session.em_enabled is True
        assert ctrl.session.sh_enabled is False


# ===========================================================
# Validate — session errors
# ===========================================================

class TestAfControllerValidateErrors:

    def test_empty_is_invalid(self, ctrl):
        result = ctrl.validate()
        assert not result

    def test_valid_session(self, ctrl, nqs):
        nqs.templates.add("T1")
        nqs.net_matches[("T1", "vdd", False)] = ["vdd"]
        ctrl.set_template("T1")
        ctrl.set_net("vdd")
        ctrl.set_af_value(0.5)
        ctrl.set_em_mode(True)
        ctrl.set_sh_mode(False)
        result = ctrl.validate()
        assert result
        assert result.warnings == []


# ===========================================================
# Validate — service-level warnings
# ===========================================================

class TestAfControllerValidateWarnings:

    def test_no_matches_produces_warning(self, ctrl, nqs):
        # No net_matches configured → find_matches returns []
        ctrl.set_net("nonexistent")
        ctrl.set_af_value(0.5)
        ctrl.set_em_mode(True)
        ctrl.set_sh_mode(False)
        result = ctrl.validate()
        assert result.is_valid  # warnings don't block
        assert len(result.warnings) == 1
        assert "no matches" in result.warnings[0].lower()

    def test_matches_exist_no_warning(self, ctrl, nqs):
        nqs.templates.add("T1")
        nqs.net_matches[("T1", "vdd", False)] = ["vdd"]
        ctrl.set_template("T1")
        ctrl.set_net("vdd")
        ctrl.set_af_value(0.5)
        ctrl.set_em_mode(True)
        ctrl.set_sh_mode(False)
        result = ctrl.validate()
        assert result.is_valid
        assert result.warnings == []

    def test_warnings_skipped_when_session_invalid(self, ctrl, nqs):
        # Session invalid (no net) → service check not attempted
        ctrl.set_template("T1")
        ctrl.set_af_value(0.5)
        ctrl.set_em_mode(True)
        ctrl.set_sh_mode(False)
        result = ctrl.validate()
        assert not result.is_valid
        assert result.warnings == []


# ===========================================================
# to_line_data / from_line_data
# ===========================================================

class TestAfControllerSerialization:

    def test_to_line_data(self, ctrl):
        ctrl.set_template("T1")
        ctrl.set_template_regex(False)
        ctrl.set_net("vdd")
        ctrl.set_net_regex(False)
        ctrl.set_af_value(0.8)
        ctrl.set_em_mode(True)
        ctrl.set_sh_mode(True)
        data = ctrl.to_line_data()
        assert isinstance(data, AfLineData)
        assert data.template == "T1"
        assert data.is_template_regex is False
        assert data.net == "vdd"
        assert data.is_net_regex is False
        assert data.af_value == 0.8
        assert data.is_em_enabled is True
        assert data.is_sh_enabled is True

    def test_from_line_data_round_trip(self, nqs):
        ctrl1 = AfEditController(nqs)
        ctrl1.start_session("s1")
        ctrl1.set_template("T1")
        ctrl1.set_net("vdd")
        ctrl1.set_af_value(0.5)
        ctrl1.set_em_mode(True)
        ctrl1.set_sh_mode(False)
        data = ctrl1.to_line_data()

        ctrl2 = AfEditController(nqs)
        ctrl2.start_session("s2")
        ctrl2.from_line_data(data)
        assert ctrl2.session.template_name == "T1"
        assert ctrl2.session.net_name == "vdd"
        assert ctrl2.session.af_value == 0.5
        assert ctrl2.session.em_enabled is True
        assert ctrl2.session.sh_enabled is False
