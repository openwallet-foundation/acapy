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

from .. import manager as test_module
from ..messages.service import Service as ServiceMessage
from ..message_types import INVITATION

from aries_cloudagent.protocols.connections.v1_0.manager import ConnectionManager


class TestConfig:

    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_endpoint = "http://localhost"

    test_target_did = "GbuDUYXaUZRfHD2jeDuQuP"

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
            did, "indy", "IndyAgent", recip_keys, router_keys, TestConfig.test_endpoint
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
        self.ledger = async_mock.create_autospec(BaseLedger)
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.context.injector.bind_instance(BaseLedger, self.ledger)
        self.context.update_settings(
            {
                "default_endpoint": TestConfig.test_endpoint,
                "default_label": "This guy",
                "additional_endpoints": ["http://aries.ca/another-endpoint"],
                "debug.auto_accept_invites": True,
                "debug.auto_accept_requests": True,
            }
        )

        self.manager = OutOfBandManager(self.context)
        self.test_conn_rec = ConnectionRecord(
            my_did=TestConfig.test_did,
            their_did=TestConfig.test_target_did,
            their_role=None,
            state=ConnectionRecord.STATE_ACTIVE,
        )

    async def test_create_invitation_handshake_succeeds(self):
        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            BaseWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did, TestConfig.test_verkey, None
            )
            inv_model = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                use_public_did=True,
                include_handshake=True,
                multi_use=False,
            )

            assert inv_model.invitation["@type"] == INVITATION
            assert not inv_model.invitation["request~attach"]
            assert inv_model.invitation["label"] == "This guy"
            assert inv_model.invitation["handshake_protocols"] == [
                "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/invitation"
            ]
            assert inv_model.invitation["service"] == [f"did:sov:{TestConfig.test_did}"]

    async def test_create_invitation_attachment_cred_offer(self):
        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            BaseWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            test_module.V10CredentialExchange,
            "retrieve_by_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_cxid:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did, TestConfig.test_verkey, None
            )
            mock_retrieve_cxid.return_value = async_mock.MagicMock(
                credential_offer_dict={"cred": "offer"}
            )
            inv_model = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                use_public_did=True,
                include_handshake=True,
                multi_use=False,
                attachments=[{"type": "credential-offer", "id": "dummy-id"}],
            )

            assert inv_model.invitation["request~attach"]
            mock_retrieve_cxid.assert_called_once_with(self.manager.context, "dummy-id")

    async def test_create_invitation_attachment_present_proof(self):
        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            BaseWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            test_module.V10PresentationExchange,
            "retrieve_by_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_pxid:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did, TestConfig.test_verkey, None
            )
            mock_retrieve_pxid.return_value = async_mock.MagicMock(
                presentation_request_dict={"pres": "req"}
            )
            inv_model = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                use_public_did=True,
                include_handshake=True,
                multi_use=False,
                attachments=[{"type": "present-proof", "id": "dummy-id"}],
            )

            assert inv_model.invitation["request~attach"]
            mock_retrieve_pxid.assert_called_once_with(self.manager.context, "dummy-id")

    async def test_create_invitation_attachment_x(self):
        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            BaseWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did, TestConfig.test_verkey, None
            )
            with self.assertRaises(OutOfBandManagerError):
                await self.manager.create_invitation(
                    my_endpoint=TestConfig.test_endpoint,
                    use_public_did=True,
                    include_handshake=True,
                    multi_use=False,
                    attachments=[{"having": "attachment", "is": "no", "good": "here"}],
                )

    async def test_create_invitation_local_did(self):
        inv_model = await self.manager.create_invitation(
            my_label="That guy",
            my_endpoint=TestConfig.test_endpoint,
            use_public_did=False,
            include_handshake=True,
            multi_use=False,
        )

        assert inv_model.invitation["@type"] == INVITATION
        assert not inv_model.invitation["request~attach"]
        assert inv_model.invitation["label"] == "That guy"
        assert inv_model.invitation["handshake_protocols"] == [
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/invitation"
        ]
        service = inv_model.invitation["service"][0]
        assert service["id"] == "#inline"
        assert service["type"] == "did-communication"
        assert len(service["recipientKeys"]) == 1
        assert not service["routingKeys"]
        assert service["serviceEndpoint"] == TestConfig.test_endpoint

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
                TestConfig.test_did, TestConfig.test_verkey, None
            )

            conn_inv_cls.deserialize.return_value = async_mock.MagicMock()

            conn_inv_mock = async_mock.MagicMock()
            inv_message_cls.deserialize.return_value = conn_inv_mock
            conn_inv_mock.service_blocks = [async_mock.MagicMock()]
            conn_inv_mock.handshake_protocols = [
                "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/invitation"
            ]

            inv_model = await self.manager.receive_invitation(conn_inv_mock)

    async def test_receive_invitation_no_service_blocks_nor_dids(self):
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
                TestConfig.test_did, TestConfig.test_verkey, None
            )

            conn_inv_cls.deserialize.return_value = async_mock.MagicMock()

            conn_inv_mock = async_mock.MagicMock()
            inv_message_cls.deserialize.return_value = conn_inv_mock
            conn_inv_mock.service_blocks = []
            conn_inv_mock.service_dids = []
            conn_inv_mock.handshake_protocols = [
                "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/invitation"
            ]
            with self.assertRaises(OutOfBandManagerError):
                await self.manager.receive_invitation(conn_inv_mock)

    async def test_receive_invitation_service_block_did_format(self):
        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            ConnectionManager, "receive_invitation", autospec=True
        ) as conn_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.ConnectionInvitation",
            autospec=True,
        ) as conn_inv_cls:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint

            conn_inv_cls.deserialize.return_value = async_mock.MagicMock()

            conn_inv_mock = async_mock.MagicMock()
            inv_message_cls.deserialize.return_value = conn_inv_mock
            conn_inv_mock.service_blocks = []
            conn_inv_mock.service_dids = [TestConfig.test_did]
            conn_inv_mock.handshake_protocols = [
                "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/invitation"
            ]

            inv_model = await self.manager.receive_invitation(conn_inv_mock)
            assert inv_model.invitation["service"]

    async def test_receive_invitation_attachment_x(self):
        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            ConnectionManager, "receive_invitation", autospec=True
        ) as conn_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.ConnectionInvitation",
            autospec=True,
        ) as conn_inv_cls:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint

            conn_inv_cls.deserialize.return_value = async_mock.MagicMock()

            conn_inv_mock = async_mock.MagicMock()
            inv_message_cls.deserialize.return_value = conn_inv_mock
            conn_inv_mock.service_blocks = []
            conn_inv_mock.service_dids = [TestConfig.test_did]
            conn_inv_mock.handshake_protocols = [
                "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/invitation"
            ]
            conn_inv_mock.request_attach = [
                {"having": "attachment", "is": "no", "good": "here"}
            ]

            with self.assertRaises(OutOfBandManagerError):
                await self.manager.receive_invitation(conn_inv_mock)

    async def test_receive_invitation_req_pres_attachment_x(self):
        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            ConnectionManager, "receive_invitation", autospec=True
        ) as conn_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.ConnectionInvitation",
            autospec=True,
        ) as conn_inv_cls:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint

            conn_inv_cls.deserialize.return_value = async_mock.MagicMock()

            conn_inv_mock = async_mock.MagicMock()
            inv_message_cls.deserialize.return_value = conn_inv_mock
            conn_inv_mock.service_blocks = []
            conn_inv_mock.service_dids = [TestConfig.test_did]
            conn_inv_mock.handshake_protocols = []
            conn_inv_mock.request_attach = [
                async_mock.MagicMock(
                    data=async_mock.MagicMock(
                        json={
                            "@type": (
                                "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec"
                                "/present-proof/1.0/request-presentation"
                            )
                        }
                    )
                )
            ]

            with self.assertRaises(OutOfBandManagerNotImplementedError):
                await self.manager.receive_invitation(conn_inv_mock)

    async def test_receive_invitation_invalid_request_type_x(self):
        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            ConnectionManager, "receive_invitation", autospec=True
        ) as conn_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.ConnectionInvitation",
            autospec=True,
        ) as conn_inv_cls:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint

            conn_inv_cls.deserialize.return_value = async_mock.MagicMock()

            conn_inv_mock = async_mock.MagicMock()
            inv_message_cls.deserialize.return_value = conn_inv_mock
            conn_inv_mock.service_blocks = []
            conn_inv_mock.service_dids = [TestConfig.test_did]
            conn_inv_mock.handshake_protocols = []
            conn_inv_mock.request_attach = []

            with self.assertRaises(OutOfBandManagerError):
                await self.manager.receive_invitation(conn_inv_mock)
