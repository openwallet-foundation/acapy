"""Test OOB Manager."""
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....connections.models.conn_record import ConnRecord
from .....connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from .....core.in_memory import InMemoryProfile
from .....ledger.base import BaseLedger
from .....messaging.responder import BaseResponder, MockResponder
from .....multitenant.manager import MultitenantManager
from .....protocols.didexchange.v1_0.manager import DIDXManager
from .....protocols.connections.v1_0.manager import ConnectionManager
from .....protocols.present_proof.v1_0.manager import PresentationManager
from .....protocols.present_proof.v1_0.message_types import PRESENTATION_REQUEST
from .....wallet.base import DIDInfo, KeyInfo
from .....wallet.in_memory import InMemoryWallet
from .....wallet.util import did_key_to_naked
from ....didcomm_prefix import DIDCommPrefix
from .. import manager as test_module
from ..messages.invitation import InvitationMessage, InvitationMessageSchema
from ..messages.reuse import HandshakeReuse
from ..messages.reuse_accept import HandshakeReuseAccept
from ..messages.problem_report import ProblemReport, ProblemReportReason
from ..manager import (
    OutOfBandManager,
    OutOfBandManagerError,
    OutOfBandManagerNotImplementedError,
)
from ..models.invitation import InvitationRecord
from .....multitenant.manager import MultitenantManager
from ..message_types import INVITATION
from uuid import UUID
from ....issue_credential.v1_0.models.credential_exchange import V10CredentialExchange
from .....wallet.util import naked_to_did_key
from .....connections.models.connection_target import ConnectionTarget
from .....transport.inbound.receipt import MessageReceipt


class TestConfig:

    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_endpoint = "http://localhost"
    DIDX_INVITATION = "didexchange/1.0"
    CONNECTION_INVITATION = "connections/1.0"
    test_target_did = "GbuDUYXaUZRfHD2jeDuQuP"
    their_public_did = "55GkHamhTU1ZbTbV2ab9DE"

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
        self.responder = MockResponder()
        self.responder.send = async_mock.CoroutineMock()

        self.session = InMemoryProfile.test_session(
            {
                "default_endpoint": TestConfig.test_endpoint,
                "default_label": "This guy",
                "additional_endpoints": ["http://aries.ca/another-endpoint"],
                "debug.auto_accept_invites": True,
                "debug.auto_accept_requests": True,
            }
        )
        self.session.context.injector.bind_instance(BaseResponder, self.responder)
        self.mt_mgr = async_mock.MagicMock()
        self.mt_mgr = async_mock.create_autospec(MultitenantManager)
        self.session.context.injector.bind_instance(MultitenantManager, self.mt_mgr)

        self.multitenant_mgr = async_mock.MagicMock(MultitenantManager, autospec=True)
        self.session.context.injector.bind_instance(
            MultitenantManager, self.multitenant_mgr
        )

        self.ledger = async_mock.create_autospec(BaseLedger)
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.session.context.injector.bind_instance(BaseLedger, self.ledger)

        self.manager = OutOfBandManager(self.session)
        assert self.manager.session

        self.test_conn_rec = ConnRecord(
            my_did=TestConfig.test_did,
            their_did=TestConfig.test_target_did,
            their_role=None,
            state=ConnRecord.State.COMPLETED,
            their_public_did=self.their_public_did,
        )

    async def test_create_invitation_handshake_succeeds(self):
        self.manager.session.context.update_settings({"public_invites": True})

        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did, TestConfig.test_verkey, None
            )
            invi_rec = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                public=True,
                include_handshake=True,
                multi_use=False,
            )

            assert invi_rec.invitation["@type"] == DIDCommPrefix.qualify_current(
                INVITATION
            )
            assert not invi_rec.invitation.get("request~attach")
            assert invi_rec.invitation["label"] == "This guy"
            assert (
                DIDCommPrefix.qualify_current(test_module.DIDX_INVITATION)
                in invi_rec.invitation["handshake_protocols"]
            )
            assert invi_rec.invitation["service"] == [f"did:sov:{TestConfig.test_did}"]

    async def test_create_invitation_multitenant_local(self):
        self.manager.session.context.update_settings(
            {
                "multitenant.enabled": True,
                "wallet.id": "test_wallet",
            }
        )

        self.multitenant_mgr.add_key = async_mock.CoroutineMock()

        with async_mock.patch.object(
            InMemoryWallet, "create_signing_key", autospec=True
        ) as mock_wallet_create_signing_key:
            mock_wallet_create_signing_key.return_value = KeyInfo(
                TestConfig.test_verkey, None
            )
            await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                include_handshake=True,
                multi_use=False,
            )

            self.multitenant_mgr.add_key.assert_called_once_with(
                "test_wallet", TestConfig.test_verkey
            )

    async def test_create_invitation_multitenant_public(self):
        self.manager.session.context.update_settings(
            {
                "multitenant.enabled": True,
                "wallet.id": "test_wallet",
                "public_invites": True,
            }
        )

        self.multitenant_mgr.add_key = async_mock.CoroutineMock()

        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, None
            )
            await self.manager.create_invitation(include_handshake=True, public=True)

            self.multitenant_mgr.add_key.assert_called_once_with(
                "test_wallet", TestConfig.test_verkey, skip_if_exists=True
            )

    async def test_create_invitation_no_handshake_no_attachments_x(self):
        with self.assertRaises(OutOfBandManagerError) as context:
            await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                public=True,
                include_handshake=False,
                multi_use=False,
            )
            assert "Invitation must include" in str(context.exception)

    async def test_create_invitation_attachment_cred_offer(self):
        self.manager.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            V10CredentialExchange,
            "retrieve_by_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_cxid:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did, TestConfig.test_verkey, None
            )
            mock_retrieve_cxid.return_value = async_mock.MagicMock(
                credential_offer_dict={"cred": "offer"}
            )
            with self.assertRaises(OutOfBandManagerError) as context:
                invi_rec = await self.manager.create_invitation(
                    my_endpoint=TestConfig.test_endpoint,
                    public=True,
                    include_handshake=True,
                    multi_use=False,
                    attachments=[{"type": "credential-offer", "id": "dummy-id"}],
                )
                assert "Unknown attachment type" in str(context.exception)

    async def test_create_invitation_attachment_present_proof(self):
        self.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
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
            invi_rec = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                public=True,
                include_handshake=True,
                multi_use=False,
                attachments=[{"type": "present-proof", "id": "dummy-id"}],
            )

            assert invi_rec.invitation["request~attach"]
            mock_retrieve_pxid.assert_called_once_with(self.manager.session, "dummy-id")

    async def test_create_invitation_public_x_no_public_invites(self):
        self.session.context.update_settings({"public_invites": False})

        with self.assertRaises(OutOfBandManagerError) as context:
            await self.manager.create_invitation(
                public=True,
                my_endpoint="testendpoint",
                include_handshake=True,
            )
        assert "Public invitations" in str(context.exception)

    async def test_create_invitation_public_x_no_public_did(self):
        self.session.context.update_settings({"public_invites": True})

        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = None
            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager.create_invitation(
                    public=True,
                    my_endpoint="testendpoint",
                    include_handshake=True,
                )
        assert "Cannot create public invitation" in str(context.exception)

    async def test_create_invitation_x_public_multi_use(self):
        self.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did, TestConfig.test_verkey, None
            )
            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager.create_invitation(
                    public=True,
                    include_handshake=True,
                    multi_use=True,
                )
            assert "Cannot use public and multi_use" in str(context.exception)

    async def test_create_invitation_attachment_x(self):
        self.manager.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did, TestConfig.test_verkey, None
            )
            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager.create_invitation(
                    my_endpoint=TestConfig.test_endpoint,
                    public=True,
                    include_handshake=True,
                    multi_use=False,
                    attachments=[{"having": "attachment", "is": "no", "good": "here"}],
                )
            assert "Unknown attachment type" in str(context.exception)

    async def test_create_invitation_peer_did(self):
        self.manager.session.context.update_settings(
            {
                "multitenant.enabled": True,
                "wallet.id": "my-wallet",
            }
        )

        invi_rec = await self.manager.create_invitation(
            my_label="That guy",
            my_endpoint=None,
            public=False,
            include_handshake=True,
            multi_use=False,
        )

        assert invi_rec.invitation["@type"] == DIDCommPrefix.qualify_current(INVITATION)
        assert not invi_rec.invitation.get("request~attach")
        assert invi_rec.invitation["label"] == "That guy"
        assert (
            DIDCommPrefix.qualify_current(test_module.DIDX_INVITATION)
            in invi_rec.invitation["handshake_protocols"]
        )
        service = invi_rec.invitation["service"][0]
        assert service["id"] == "#inline"
        assert service["type"] == "did-communication"
        assert len(service["recipientKeys"]) == 1
        assert not service.get("routingKeys")
        assert service["serviceEndpoint"] == TestConfig.test_endpoint

    async def test_create_invitation_metadata_assigned(self):
        invi_rec = await self.manager.create_invitation(
            include_handshake=True,
            metadata={"hello": "world"},
        )
        service = invi_rec.invitation["service"][0]
        invitation_key = did_key_to_naked(service["recipientKeys"][0])
        record = await ConnRecord.retrieve_by_invitation_key(
            self.session, invitation_key
        )
        assert await record.metadata_get_all(self.session) == {"hello": "world"}

    async def test_create_invitation_x_public_metadata(self):
        self.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did, TestConfig.test_verkey, None
            )
            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager.create_invitation(
                    public=True,
                    include_handshake=True,
                    metadata={"hello": "world"},
                )
            assert "Cannot store metadata on public" in str(context.exception)

    async def test_receive_invitation_didx_service_block(self):
        self.manager.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as didx_mgr_cls, async_mock.patch.object(
            test_module,
            "InvitationMessage",
            autospec=True,
        ) as invi_msg_cls:
            didx_mgr_cls.return_value = async_mock.MagicMock(
                receive_invitation=async_mock.CoroutineMock()
            )
            mock_oob_invi = async_mock.MagicMock(
                request_attach=[],
                handshake_protocols=[
                    pfx.qualify(test_module.DIDX_INVITATION) for pfx in DIDCommPrefix
                ],
                service_dids=[],
                service_blocks=[
                    async_mock.MagicMock(
                        recipient_keys=["dummy"],
                        routing_keys=[],
                    )
                ],
            )
            invi_msg_cls.deserialize.return_value = mock_oob_invi

            await self.manager.receive_invitation(mock_oob_invi)

    async def test_receive_invitation_connection_mock(self):
        self.manager.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as conn_mgr_cls, async_mock.patch.object(
            test_module,
            "InvitationMessage",
            autospec=True,
        ) as invi_msg_cls, async_mock.patch.object(
            self.manager,
            "receive_invitation",
            async_mock.CoroutineMock(),
        ) as mock_receive_invitation:
            mock_receive_invitation.return_value = self.test_conn_rec.serialize()
            conn_mgr_cls.return_value = async_mock.MagicMock(
                receive_invitation=async_mock.CoroutineMock()
            )
            mock_oob_invi = async_mock.MagicMock(
                handshake_protocols=[
                    pfx.qualify(test_module.CONNECTION_INVITATION)
                    for pfx in DIDCommPrefix
                ],
                service_dids=[],
                label="test",
                _id="test123",
                service_blocks=[
                    async_mock.MagicMock(
                        recipient_keys=[
                            naked_to_did_key(
                                "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
                            )
                        ],
                        routing_keys=[],
                        service_endpoint="http://localhost",
                    )
                ],
                request_attach=[],
            )
            invi_msg_cls.deserialize.return_value = mock_oob_invi
            result = await self.manager.receive_invitation(mock_oob_invi)
            assert result == self.test_conn_rec.serialize()

    async def test_receive_invitation_connection(self):
        self.manager.session.context.update_settings({"public_invites": True})
        oob_invi_rec = await self.manager.create_invitation(
            auto_accept=True,
            public=False,
            include_handshake=True,
            use_connections=True,
            multi_use=False,
        )

        result = await self.manager.receive_invitation(
            invi_msg=InvitationMessage.deserialize(oob_invi_rec.invitation),
            use_existing_connection=True,
            auto_accept=True,
        )
        conn_id = UUID(result.get("connection_id"), version=4)
        assert (
            conn_id.hex == result.get("connection_id").replace("-", "")
            and len(result.get("connection_id")) > 5
        )

    async def test_receive_invitation_no_service_blocks_nor_dids(self):
        self.manager.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            test_module, "InvitationMessage", async_mock.MagicMock()
        ) as invi_msg_cls:
            mock_invi_msg = async_mock.MagicMock(
                service_blocks=[],
                service_dids=[],
            )
            invi_msg_cls.deserialize.return_value = mock_invi_msg
            with self.assertRaises(OutOfBandManagerError):
                await self.manager.receive_invitation(mock_invi_msg)

    async def test_receive_invitation_service_did(self):
        self.manager.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as didx_mgr_cls, async_mock.patch.object(
            test_module,
            "InvitationMessage",
            autospec=True,
        ) as invi_msg_cls:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint
            didx_mgr_cls.return_value = async_mock.MagicMock(
                receive_invitation=async_mock.CoroutineMock()
            )
            mock_oob_invi = async_mock.MagicMock(
                handshake_protocols=[
                    pfx.qualify(test_module.DIDX_INVITATION) for pfx in DIDCommPrefix
                ],
                service_dids=[TestConfig.test_did],
                service_blocks=[],
                request_attach=[],
            )
            invi_msg_cls.deserialize.return_value = mock_oob_invi

            invi_rec = await self.manager.receive_invitation(mock_oob_invi)
            assert invi_rec.invitation["service"]

    async def test_receive_invitation_attachment_x(self):
        self.manager.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint

            mock_oob_invi = async_mock.MagicMock(
                service_blocks=[],
                service_dids=[TestConfig.test_did],
                handshake_protocols=[
                    pfx.qualify(test_module.DIDX_INVITATION) for pfx in DIDCommPrefix
                ],
                request_attach=[{"having": "attachment", "is": "no", "good": "here"}],
            )
            inv_message_cls.deserialize.return_value = mock_oob_invi

            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager.receive_invitation(mock_oob_invi)
                assert (
                    "request~attach is not properly formatted as data is missing"
                    in str(context.exception)
                )

    async def test_receive_invitation_req_pres_attachment_x(self):
        self.manager.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint

            mock_oob_invi = async_mock.MagicMock(
                handshake_protocols=[
                    pfx.qualify(test_module.DIDX_INVITATION) for pfx in DIDCommPrefix
                ],
                service_dids=[TestConfig.test_did],
                service_blocks=[],
                request_attach=[
                    async_mock.MagicMock(
                        data=async_mock.MagicMock(
                            json={
                                "@type": DIDCommPrefix.qualify_current(
                                    PRESENTATION_REQUEST
                                )
                            }
                        )
                    ),
                ],
            )
            inv_message_cls.deserialize.return_value = mock_oob_invi

            with self.assertRaises(OutOfBandManagerError) as context:
                result = await self.manager.receive_invitation(mock_oob_invi)
                conn_id = UUID(result.get("connection_id"), version=4)
                assert (
                    conn_id.hex == result.get("connection_id")
                    and len(result.get("connection_id")) > 5
                )

    async def test_receive_invitation_invalid_request_type_x(self):
        self.manager.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint

            mock_oob_invi = async_mock.MagicMock(
                service_blocks=[],
                service_dids=[TestConfig.test_did],
                handshake_protocols=[],
                request_attach=[],
            )
            inv_message_cls.deserialize.return_value = mock_oob_invi

            with self.assertRaises(OutOfBandManagerError):
                await self.manager.receive_invitation(mock_oob_invi)

    async def test_find_existing_connection(self):
        test_conn_rec = ConnRecord(
            my_did=TestConfig.test_did,
            their_did=TestConfig.test_target_did,
            their_role=None,
            state=ConnRecord.State.COMPLETED,
            their_public_did=self.their_public_did,
        )
        await test_conn_rec.save(self.session)

        tag_filter = {}
        post_filter = {}
        post_filter["their_public_did"] = "not_addded"
        conn_record = await self.manager.find_existing_connection(
            tag_filter, post_filter
        )
        assert conn_record == None

        post_filter["their_public_did"] = self.their_public_did
        post_filter["state"] = "active"
        conn_record = await self.manager.find_existing_connection(
            tag_filter, post_filter
        )
        assert conn_record == test_conn_rec
        await test_conn_rec.delete_record(self.session)

    async def test_check_reuse_msg_state(self):
        await self.test_conn_rec.save(self.session)
        await self.test_conn_rec.metadata_set(
            self.session, "reuse_msg_state", "accepted"
        )
        assert await self.manager.check_reuse_msg_state(self.test_conn_rec) is None

    async def test_create_handshake_reuse_msg(self):
        self.manager.session.context.update_settings({"public_invites": True})
        await self.test_conn_rec.save(self.session)
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint
            oob_mgr_fetch_conn.return_value = ConnectionTarget(
                did=TestConfig.test_did,
                endpoint=TestConfig.test_endpoint,
                recipient_keys=TestConfig.test_verkey,
                sender_key=TestConfig.test_verkey,
            )
            oob_invi = InvitationMessage()

            await self.manager.create_handshake_reuse_message(
                oob_invi, self.test_conn_rec
            )
            assert (
                len(await self.test_conn_rec.metadata_get(self.session, "reuse_msg_id"))
                > 6
            )
            assert (
                await self.test_conn_rec.metadata_get(self.session, "reuse_msg_state")
                == "initial"
            )

    async def test_recieve_reuse_message_existing_found(self):
        self.manager.session.context.update_settings({"public_invites": True})
        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
        )
        reuse_msg = HandshakeReuse()
        reuse_msg.assign_thread_id(thid="test_123", pthid="test_123")
        self.test_conn_rec.invitation_msg_id = "test_123"
        self.test_conn_rec.state = ConnRecord.State.COMPLETED.rfc160
        await self.test_conn_rec.save(self.session)
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn, async_mock.patch.object(
            OutOfBandManager,
            "find_existing_connection",
            autospec=True,
        ) as oob_mgr_find_existing_conn, async_mock.patch.object(
            InvitationRecord,
            "retrieve_by_tag_filter",
            autospec=True,
        ) as retrieve_invi_rec:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint
            oob_mgr_find_existing_conn.return_value = self.test_conn_rec
            oob_mgr_fetch_conn.return_value = ConnectionTarget(
                did=TestConfig.test_did,
                endpoint=TestConfig.test_endpoint,
                recipient_keys=TestConfig.test_verkey,
                sender_key=TestConfig.test_verkey,
            )
            oob_invi = InvitationMessage()
            retrieve_invi_rec.return_value = InvitationRecord(
                invi_msg_id="test_123", multi_use=False
            )
            await self.manager.receive_reuse_message(reuse_msg, receipt)
            assert (
                len(
                    await ConnRecord.query(
                        session=self.session,
                        tag_filter={},
                        post_filter_positive={"invitation_msg_id": "test_123"},
                        alt=True,
                    )
                )
                == 1
            )

    async def test_recieve_reuse_message_existing_not_found(self):
        self.manager.session.context.update_settings({"public_invites": True})
        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            sender_did="test_did",
        )
        reuse_msg = HandshakeReuse()
        reuse_msg.assign_thread_id(thid="test_123", pthid="test_123")
        self.test_conn_rec.invitation_msg_id = "test_123"
        self.test_conn_rec.state = ConnRecord.State.REQUEST.rfc160
        await self.test_conn_rec.save(self.session)
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn, async_mock.patch.object(
            ConnRecord,
            "query",
            autospec=True,
        ) as conn_rec_query, async_mock.patch.object(
            InvitationRecord,
            "retrieve_by_tag_filter",
            autospec=True,
        ) as retrieve_invi_rec, async_mock.patch.object(
            OutOfBandManager,
            "find_existing_connection",
            autospec=True,
        ) as oob_mgr_find_existing_conn:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint
            conn_rec_query.return_value = [self.test_conn_rec]
            oob_mgr_find_existing_conn.return_value = None
            oob_mgr_fetch_conn.return_value = ConnectionTarget(
                did=TestConfig.test_did,
                endpoint=TestConfig.test_endpoint,
                recipient_keys=TestConfig.test_verkey,
                sender_key=TestConfig.test_verkey,
            )
            oob_invi = InvitationMessage()
            retrieve_invi_rec.return_value = InvitationRecord(
                invi_msg_id="test_123", multi_use=False
            )
            await self.manager.receive_reuse_message(reuse_msg, receipt)

    async def test_recieve_reuse_accepeted(self):
        self.manager.session.context.update_settings({"public_invites": True})
        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            sender_did="test_did",
        )
        reuse_msg_accepted = HandshakeReuseAccept()
        reuse_msg_accepted.assign_thread_id(thid="test_123", pthid="test_123")
        self.test_conn_rec.invitation_msg_id = "test_123"
        self.test_conn_rec.state = ConnRecord.State.COMPLETED.rfc160
        await self.test_conn_rec.save(self.session)
        await self.test_conn_rec.metadata_set(self.session, "reuse_msg_id", "test_123")
        await self.test_conn_rec.metadata_set(
            self.session, "reuse_msg_state", "initial"
        )
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint

            await self.manager.receive_reuse_accepted_message(
                reuse_msg_accepted, receipt, self.test_conn_rec
            )
            assert (
                await self.test_conn_rec.metadata_get(self.session, "reuse_msg_state")
                == "accepted"
            )

    async def test_recieve_reuse_accepeted_invalid_conn(self):
        self.manager.session.context.update_settings({"public_invites": True})
        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            sender_did="test_did",
        )
        reuse_msg_accepted = HandshakeReuseAccept()
        reuse_msg_accepted.assign_thread_id(thid="test_123", pthid="test_123")
        test_invalid_conn = ConnRecord(
            my_did="Test",
            their_did="Test",
            invitation_msg_id="test_456",
            connection_id="12345678-1234-5678-1234-567812345678",
        )
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint
            with self.assertRaises(AssertionError) as context:
                await self.manager.receive_reuse_accepted_message(
                    reuse_msg_accepted, receipt, test_invalid_conn
                )

    async def test_problem_report_received_not_active(self):
        self.manager.session.context.update_settings({"public_invites": True})
        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            sender_did="test_did",
        )
        problem_report = ProblemReport(
            problem_code=ProblemReportReason.EXISTING_CONNECTION_NOT_ACTIVE.value,
            explain="test",
        )
        problem_report.assign_thread_id(thid="test_123", pthid="test_123")
        self.test_conn_rec.invitation_msg_id = "test_123"
        self.test_conn_rec.state = ConnRecord.State.COMPLETED.rfc160
        await self.test_conn_rec.save(self.session)
        await self.test_conn_rec.metadata_set(self.session, "reuse_msg_id", "test_123")
        await self.test_conn_rec.metadata_set(
            self.session, "reuse_msg_state", "initial"
        )
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint

            await self.manager.receive_problem_report(
                problem_report, receipt, self.test_conn_rec
            )
            assert (
                await self.test_conn_rec.metadata_get(self.session, "reuse_msg_state")
                == "not_accepted"
            )

    async def test_problem_report_received_not_exists(self):
        self.manager.session.context.update_settings({"public_invites": True})
        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            sender_did="test_did",
        )
        problem_report = ProblemReport(
            problem_code=ProblemReportReason.EXISTING_CONNECTION_DOES_NOT_EXISTS.value,
            explain="test",
        )
        problem_report.assign_thread_id(thid="test_123", pthid="test_123")
        self.test_conn_rec.invitation_msg_id = "test_123"
        self.test_conn_rec.state = ConnRecord.State.COMPLETED.rfc160
        await self.test_conn_rec.save(self.session)
        await self.test_conn_rec.metadata_set(self.session, "reuse_msg_id", "test_123")
        await self.test_conn_rec.metadata_set(
            self.session, "reuse_msg_state", "initial"
        )
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint

            await self.manager.receive_problem_report(
                problem_report, receipt, self.test_conn_rec
            )
            assert (
                await self.test_conn_rec.metadata_get(self.session, "reuse_msg_state")
                == "not_accepted"
            )

    async def test_problem_report_received_invalid_conn(self):
        self.manager.session.context.update_settings({"public_invites": True})
        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            sender_did="test_did",
        )
        problem_report = ProblemReport(
            problem_code=ProblemReportReason.EXISTING_CONNECTION_DOES_NOT_EXISTS.value,
            explain="test",
        )
        problem_report.assign_thread_id(thid="test_123", pthid="test_123")
        test_invalid_conn = ConnRecord(
            my_did="Test",
            their_did="Test",
            invitation_msg_id="test_456",
            connection_id="12345678-1234-5678-1234-567812345678",
        )
        with async_mock.patch.object(
            self.ledger, "get_key_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_key_for_did, async_mock.patch.object(
            self.ledger, "get_endpoint_for_did", async_mock.CoroutineMock()
        ) as mock_ledger_get_endpoint_for_did, async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn:
            mock_ledger_get_key_for_did.return_value = TestConfig.test_verkey
            mock_ledger_get_endpoint_for_did.return_value = TestConfig.test_endpoint

            with self.assertRaises(AssertionError) as context:
                await self.manager.receive_problem_report(
                    problem_report, receipt, test_invalid_conn
                )
