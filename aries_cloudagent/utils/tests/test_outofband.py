from asynctest import mock, TestCase

from ...messaging.agent_message import AgentMessage
from ...protocols.out_of_band.v1_0.messages.invitation import Invitation
from ...wallet.base import DIDInfo

from .. import outofband as test_module


class TestOutOfBand(TestCase):
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_did_info = DIDInfo(test_did, test_verkey, None)

    def test_serialize_oob(self):
        invi = Invitation(
            comment="my sister", label=u"ma sœur", service=[TestOutOfBand.test_did]
        )

        result = test_module.serialize_outofband(
            invi, TestOutOfBand.test_did_info, "http://1.2.3.4:8081"
        )
        assert "?d_m=" in result
