import pytest

from doc_types.af import AFEditSessionState


@pytest.fixture
def session():
    return AFEditSessionState("s1")


# ===========================================================
# Mutation
# ===========================================================

class TestAfMutation:

    def test_set_template(self, session):
        session.template_name = "T1"
        session.template_regex_mode = True
        assert session.template_name == "T1"
        assert session.template_regex_mode is True

    def test_set_net(self, session):
        session.net_name = "vdd.*"
        session.net_regex_mode = True
        assert session.net_name == "vdd.*"
        assert session.net_regex_mode is True

    def test_set_af_value(self, session):
        session.af_value = 0.5
        assert session.af_value == 0.5

    def test_set_mode(self, session):
        session.em_enabled = True
        session.sh_enabled = False
        assert session.em_enabled is True
        assert session.sh_enabled is False


# ===========================================================
# Validate
# ===========================================================

class TestAfValidate:

    def test_empty_session_is_invalid(self, session):
        result = session.validate()
        assert not result

    def test_valid_session(self, session):
        session.net_name = "vdd"
        session.af_value = 0.5
        session.em_enabled = True
        result = session.validate()
        assert result

    def test_af_out_of_range_invalid(self, session):
        session.net_name = "vdd"
        session.em_enabled = True
        session.af_value = 1.5
        result = session.validate()
        assert not result

    def test_no_mode_selected_invalid(self, session):
        session.net_name = "vdd"
        session.af_value = 0.5
        result = session.validate()
        assert not result
