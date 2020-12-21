"""Test OOB Manager."""
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....connections.models.conn_record import ConnRecord
from .....connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from .....core.in_memory import InMemoryProfile
from .....ledger.base import BaseLedger
from .....messaging.responder import BaseResponder, MockResponder
from .....protocols.didexchange.v1_0.manager import DIDXManager
from .....protocols.present_proof.v1_0.message_types import PRESENTATION_REQUEST
from .....wallet.base import DIDInfo
from .....wallet.in_memory import InMemoryWallet
from .....wallet.util import did_key_to_naked
from ....didcomm_prefix import DIDCommPrefix
from .. import manager as test_module
from ..manager import (
    OutOfBandManager,
    OutOfBandManagerError,
    OutOfBandManagerNotImplementedError,
)
from ..message_types import INVITATION


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

        self.ledger = async_mock.create_autospec(BaseLedger)
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.session.context.injector.bind_instance(BaseLedger, self.ledger)

        self.manager = OutOfBandManager(self.session)
        assert self.manager.session

        self.test_conn_rec = ConnRecord(
            my_did=TestConfig.test_did,
            their_did=TestConfig.test_target_did,
            their_role=None,
            state=ConnRecord.State.COMPLETED.rfc23,
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
            invi_rec = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                public=True,
                include_handshake=True,
                multi_use=False,
                attachments=[{"type": "credential-offer", "id": "dummy-id"}],
            )

            assert invi_rec.invitation["request~attach"]
            mock_retrieve_cxid.assert_called_once_with(self.manager.session, "dummy-id")

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

    async def test_receive_invitation_service_block(self):
        self.manager.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as didx_mgr_cls, async_mock.patch.object(
            test_module,
            "InvitationMessage",
            autospec=True,
        ) as invi_msg_cls, async_mock.patch.object(
            test_module, "did_key_to_naked", async_mock.MagicMock()
        ) as did2naked:
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

            with self.assertRaises(OutOfBandManagerError):
                await self.manager.receive_invitation(mock_oob_invi)

    async def test_receive_invitation_req_pres_attachment_x(self):
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
                    pfx.qualify(PRESENTATION_REQUEST) for pfx in DIDCommPrefix
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
                    )
                ],
            )
            invi_msg_cls.deserialize.return_value = mock_oob_invi

            with self.assertRaises(OutOfBandManagerNotImplementedError):
                await self.manager.receive_invitation(mock_oob_invi)

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
