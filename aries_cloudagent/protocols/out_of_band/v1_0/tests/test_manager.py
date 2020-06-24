from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aries_cloudagent.cache.base import BaseCache
from aries_cloudagent.cache.basic import BasicCache
from aries_cloudagent.config.base import InjectorError
from aries_cloudagent.ledger.base import BaseLedger
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.connections.models.connection_target import ConnectionTarget
from aries_cloudagent.connections.models.diddoc import (
    DIDDoc,
    PublicKey,
    PublicKeyType,
    Service,
)
from aries_cloudagent.ledger.base import BaseLedger
from aries_cloudagent.messaging.responder import BaseResponder, MockResponder
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.storage.basic import BasicStorage
from aries_cloudagent.storage.error import StorageNotFoundError
from aries_cloudagent.transport.inbound.receipt import MessageReceipt
from aries_cloudagent.wallet.base import BaseWallet, DIDInfo
from aries_cloudagent.wallet.basic import BasicWallet
from aries_cloudagent.wallet.error import WalletNotFoundError

from aries_cloudagent.protocols.routing.v1_0.manager import RoutingManager

from ..manager import (
    OutOfBandManager,
    OutOfBandManagerError,
    OutOfBandManagerNotImplementedError,
)

from ..messages.service import Service as ServiceMessage

from aries_cloudagent.protocols.connections.v1_0.manager import ConnectionManager


class TestConfig:

    test_seed = "testseed000000000000000000000001"
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_endpoint = "http://localhost"

    test_target_did = "GbuDUYXaUZRfHD2jeDuQuP"
    test_target_verkey = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"

    def make_did_doc(self, did, verkey):
        doc = DIDDoc(did=did)
        controller = did
        ident = "1"
        pk_value = verkey
        pk = PublicKey(
            did, ident, pk_value, PublicKeyType.ED25519_SIG_2018, controller, False
        )
        doc.set(pk)
        recip_keys = [pk]
        router_keys = []
        service = Service(
            did, "indy", "IndyAgent", recip_keys, router_keys, self.test_endpoint
        )
        doc.set(service)
        return doc


class TestOOBManager(AsyncTestCase, TestConfig):
    def setUp(self):
        self.storage = BasicStorage()
        self.cache = BasicCache()
        self.wallet = BasicWallet()
        self.responder = MockResponder()
        self.responder.send = async_mock.CoroutineMock()

        self.context = InjectionContext(enforce_typing=False)
        self.context.injector.bind_instance(BaseStorage, self.storage)
        self.context.injector.bind_instance(BaseWallet, self.wallet)
        self.context.injector.bind_instance(BaseResponder, self.responder)
        self.context.injector.bind_instance(BaseCache, self.cache)
        self.context.injector.bind_instance(BaseLedger, async_mock.MagicMock())
        self.context.update_settings(
            {
                "default_endpoint": "http://aries.ca/endpoint",
                "default_label": "This guy",
                "additional_endpoints": ["http://aries.ca/another-endpoint"],
                "debug.auto_accept_invites": True,
                "debug.auto_accept_requests": True,
            }
        )

        self.manager = OutOfBandManager(self.context)
        self.test_conn_rec = ConnectionRecord(
            my_did=self.test_did,
            their_did=self.test_target_did,
            their_role=None,
            state=ConnectionRecord.STATE_ACTIVE,
        )

    async def test_create_invitation_handshake_succeeds(self):
        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            BaseWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, None
            )
            inv_model = await self.manager.create_invitation(
                my_label="label",
                my_endpoint="endpoint",
                use_public_did=True,
                include_handshake=True,
                multi_use=False,
            )

            assert (
                inv_model.invitation["@type"]
                == "https://didcomm.org/out-of-band/1.0/invitation"
            )
            assert not inv_model.invitation["request~attach"]
            assert inv_model.invitation["label"] == "label"
            assert inv_model.invitation["handshake_protocols"] == [
                "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/invitation"
            ]
            assert inv_model.invitation["service"] == [f"did:sov:{TestConfig.test_did}"]

    async def test_receive_invitation_bad_service_length(self):
        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            BaseWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            ConnectionManager, "create_invitation", autospec=True
        ) as conn_mgr_create_inv, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls:
            mock_wallet_get_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, None
            )

            conn_inv_mock = async_mock.MagicMock()
            inv_message_cls.deserialize.return_value = conn_inv_mock
            conn_inv_mock.service_blocks = []

            with self.assertRaises(OutOfBandManagerError):
                inv_model = await self.manager.receive_invitation(conn_inv_mock)

    async def test_receive_invitation_service_block(self):
        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            BaseWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            ConnectionManager, "receive_invitation", autospec=True
        ) as conn_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.ConnectionInvitation",
            autospec=True,
        ) as conn_inv_cls:
            mock_wallet_get_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, None
            )

            conn_inv_cls.deserialize.return_value = async_mock.MagicMock()

            conn_inv_mock = async_mock.MagicMock()
            inv_message_cls.deserialize.return_value = conn_inv_mock
            conn_inv_mock.service_blocks = [async_mock.MagicMock()]
            conn_inv_mock.handshake_protocols = [
                "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/invitation"
            ]

            inv_model = await self.manager.receive_invitation(conn_inv_mock)
