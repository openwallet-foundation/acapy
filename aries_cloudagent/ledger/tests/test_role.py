from unittest import TestCase

from ..base import Role


class TestRole(TestCase):
    def test_role(self):
        assert Role.get(2) is Role.STEWARD
        assert Role.get(0) is Role.TRUSTEE
        assert Role.get(101) is Role.ENDORSER
        assert Role.get(201) is Role.NETWORK_MONITOR
        assert Role.get(None) is Role.USER
        assert Role.get(-1) is None
        assert Role.get("user") is Role.USER
        assert Role.get("steward") is Role.STEWARD
        assert Role.get("trustee") is Role.TRUSTEE
        assert Role.get("endorser") is Role.ENDORSER
        assert Role.get("network_monitor") is Role.NETWORK_MONITOR
        assert Role.get("ROLE_REMOVE") is None

        assert Role.STEWARD.to_indy_num_str() == "2"
        assert Role.TRUSTEE.to_indy_num_str() == "0"
        assert Role.ENDORSER.to_indy_num_str() == "101"
        assert Role.NETWORK_MONITOR.to_indy_num_str() == "201"
        assert Role.USER.to_indy_num_str() is None
        assert Role.ROLE_REMOVE.to_indy_num_str() == ""

        assert Role.STEWARD.token() == "STEWARD"
        assert Role.TRUSTEE.token() == "TRUSTEE"
        assert Role.ENDORSER.token() == "ENDORSER"
        assert Role.NETWORK_MONITOR.token() == "NETWORK_MONITOR"
        assert Role.USER.token() is None
        assert Role.ROLE_REMOVE.to_indy_num_str() == ""
