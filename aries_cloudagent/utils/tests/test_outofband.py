from asynctest import TestCase

from ...protocols.out_of_band.v1_0.messages.invitation import InvitationMessage
from ...wallet.key_type import KeyType
from ...wallet.did_method import DIDMethod
from ...wallet.did_info import DIDInfo

from .. import outofband as test_module


class TestOutOfBand(TestCase):
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_did_info = DIDInfo(
        test_did, test_verkey, None, method=DIDMethod.SOV, key_type=KeyType.ED25519
    )

    def test_serialize_oob(self):
        invi = InvitationMessage(
            comment="my sister", label=u"ma sœur", services=[TestOutOfBand.test_did]
        )

        result = test_module.serialize_outofband(
            invi, TestOutOfBand.test_did_info, "http://1.2.3.4:8081"
        )
        assert "?d_m=" in result
