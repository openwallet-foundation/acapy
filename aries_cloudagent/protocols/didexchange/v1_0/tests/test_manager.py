import json

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from .....cache.base import BaseCache
from .....cache.in_memory import InMemoryCache
from .....connections.models.conn_record import ConnRecord
from .....connections.models.connection_target import ConnectionTarget
from .....connections.models.diddoc import (
    DIDDoc,
    PublicKey,
    PublicKeyType,
    Service,
)
from .....core.in_memory import InMemoryProfile
from .....messaging.responder import BaseResponder, MockResponder
from .....messaging.decorators.attach_decorator import AttachDecorator
from .....storage.error import StorageNotFoundError
from .....transport.inbound.receipt import MessageReceipt
from .....wallet.base import DIDInfo
from .....wallet.in_memory import InMemoryWallet

from ....out_of_band.v1_0.manager import OutOfBandManager
from ....out_of_band.v1_0.messages.invitation import InvitationMessage
from ....out_of_band.v1_0.messages.service import Service as OOBService

from .. import manager as test_module
from ..manager import DIDXManager, DIDXManagerError


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
            did, "indy", "IndyAgent", recip_keys, router_keys, TestConfig.test_endpoint
        )
        doc.set(service)
        return doc


class TestDidExchangeManager(AsyncTestCase, TestConfig):
    async def setUp(self):
        self.responder = MockResponder()
        self.responder.send = async_mock.CoroutineMock()

        self.session = InMemoryProfile.test_session(
            {
                "default_endpoint": "http://aries.ca/endpoint",
                "default_label": "This guy",
                "additional_endpoints": ["http://aries.ca/another-endpoint"],
                "debug.auto_accept_invites": True,
                "debug.auto_accept_requests": True,
            },
            bind={BaseResponder: self.responder, BaseCache: InMemoryCache()},
        )
        self.context = self.session.context

        self.did_info = await self.session.wallet.create_local_did()

        self.manager = DIDXManager(self.session)
        assert self.manager.session
        self.oob_manager = OutOfBandManager(self.session)

    async def test_verify_diddoc(self):
        did_doc = self.make_did_doc(
            TestConfig.test_target_did,
            TestConfig.test_target_verkey,
        )
        did_doc_attach = AttachDecorator.from_indy_dict(did_doc.serialize())
        with self.assertRaises(DIDXManagerError):
            await self.manager.verify_diddoc(self.session.wallet, did_doc_attach)

        await did_doc_attach.data.sign(self.did_info.verkey, self.session.wallet)

        await self.manager.verify_diddoc(self.session.wallet, did_doc_attach)

        did_doc_attach.data.base64_ = "YmFpdCBhbmQgc3dpdGNo"
        with self.assertRaises(DIDXManagerError):
            await self.manager.verify_diddoc(self.session.wallet, did_doc_attach)

    async def test_receive_invitation(self):
        invi_rec = await self.oob_manager.create_invitation(
            my_endpoint="testendpoint",
            include_handshake=True,
        )

        invitee_record = await self.manager.receive_invitation(
            InvitationMessage.deserialize(invi_rec.invitation)
        )
        assert invitee_record.state == ConnRecord.State.REQUEST.rfc23

    async def test_receive_invitation_no_auto_accept(self):
        invi_rec = await self.oob_manager.create_invitation(
            my_endpoint="testendpoint",
            include_handshake=True,
        )

        invitee_record = await self.manager.receive_invitation(
            InvitationMessage.deserialize(invi_rec.invitation), auto_accept=False
        )
        assert invitee_record.state == ConnRecord.State.INVITATION.rfc23

    async def test_receive_invitation_bad_invitation(self):
        x_invites = [
            InvitationMessage(),
            InvitationMessage(service=[OOBService()]),
            InvitationMessage(
                service=[
                    OOBService(
                        recipient_keys=["3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"]
                    )
                ]
            ),
        ]

        for x_invite in x_invites:
            with self.assertRaises(DIDXManagerError):
                await self.manager.receive_invitation(x_invite)

    async def test_create_request(self):
        mock_conn_rec = async_mock.MagicMock(
            connection_id="dummy",
            my_did=self.did_info.did,
            their_did=TestConfig.test_target_did,
            their_role=ConnRecord.Role.RESPONDER.rfc23,
            state=ConnRecord.State.REQUEST.rfc23,
            retrieve_invitation=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    service_blocks=None,
                    service_dids=[TestConfig.test_target_did],
                )
            ),
            save=async_mock.CoroutineMock(),
        )

        with async_mock.patch.object(
            self.manager, "create_did_document", async_mock.CoroutineMock()
        ) as mock_create_did_doc:
            mock_create_did_doc.return_value = async_mock.MagicMock(
                serialize=async_mock.MagicMock(return_value={})
            )

            didx_req = await self.manager.create_request(mock_conn_rec)
            assert didx_req

    async def test_create_request_my_endpoint(self):
        mock_conn_rec = async_mock.MagicMock(
            connection_id="dummy",
            my_did=self.did_info.did,
            their_did=TestConfig.test_target_did,
            their_role=ConnRecord.Role.RESPONDER.rfc23,
            their_label="Bob",
            invitation_key=TestConfig.test_verkey,
            state=ConnRecord.State.REQUEST.rfc23,
            alias="Bob",
            retrieve_invitation=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    service_blocks=None,
                    service_dids=[TestConfig.test_target_did],
                )
            ),
            save=async_mock.CoroutineMock(),
        )

        with async_mock.patch.object(
            self.manager, "create_did_document", async_mock.CoroutineMock()
        ) as mock_create_did_doc:
            mock_create_did_doc.return_value = async_mock.MagicMock(
                serialize=async_mock.MagicMock(return_value={})
            )

            didx_req = await self.manager.create_request(
                mock_conn_rec,
                my_endpoint="http://testendpoint.com/endpoint",
            )
            assert didx_req

    async def test_receive_request_public_did(self):
        mock_request = async_mock.MagicMock()
        mock_request.did = TestConfig.test_did
        mock_request.did_doc_attach = async_mock.MagicMock(
            data=async_mock.MagicMock(
                verify=async_mock.CoroutineMock(return_value=True),
                signed=async_mock.MagicMock(
                    decode=async_mock.MagicMock(return_value="dummy-did-doc")
                ),
            )
        )
        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=True,
        )

        await self.session.wallet.create_local_did(seed=None, did=TestConfig.test_did)

        mock_conn_rec_state_request = ConnRecord.State.REQUEST
        self.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            test_module, "ConnRecord", async_mock.MagicMock()
        ) as mock_conn_rec, async_mock.patch.object(
            test_module.OOBInvitationRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as mock_oob_invi_rec_retrieve, async_mock.patch.object(
            test_module, "DIDDoc", autospec=True
        ) as mock_did_doc, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_deco, async_mock.patch.object(
            test_module, "DIDXResponse", autospec=True
        ) as mock_response, async_mock.patch.object(
            self.manager, "create_did_document", async_mock.CoroutineMock()
        ) as mock_create_did_doc:
            mock_create_did_doc.return_value = async_mock.MagicMock(
                serialize=async_mock.MagicMock(return_value={})
            )
            mock_conn_rec.State.REQUEST = mock_conn_rec_state_request
            mock_conn_rec.State.get = async_mock.MagicMock(
                return_value=mock_conn_rec_state_request
            )
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(save=async_mock.CoroutineMock())
            )
            mock_conn_rec.return_value = async_mock.MagicMock(
                accept=ConnRecord.ACCEPT_AUTO,
                my_did=None,
                state=mock_conn_rec_state_request.rfc23,
                attach_request=async_mock.CoroutineMock(),
                retrieve_request=async_mock.CoroutineMock(),
                save=async_mock.CoroutineMock(),
            )
            mock_oob_invi_rec_retrieve.return_value = async_mock.MagicMock(
                auto_accept=True,
            )
            mock_did_doc.from_json = async_mock.MagicMock(
                return_value=async_mock.MagicMock(did=TestConfig.test_did)
            )
            mock_attach_deco.from_indy_dict = async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    data=async_mock.MagicMock(sign=async_mock.CoroutineMock())
                )
            )
            mock_response.return_value = async_mock.MagicMock(
                assign_thread_from=async_mock.MagicMock(),
                assign_trace_from=async_mock.MagicMock(),
            )

            conn_rec = await self.manager.receive_request(mock_request, receipt)
            assert conn_rec

        messages = self.responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert "connection_id" in target

    async def test_receive_request_invi_not_found(self):
        mock_request = async_mock.MagicMock()
        mock_request.did = TestConfig.test_did
        mock_request.did_doc_attach = None

        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
        )

        await self.session.wallet.create_local_did(seed=None, did=TestConfig.test_did)

        with async_mock.patch.object(
            test_module, "ConnRecord", async_mock.MagicMock()
        ) as mock_conn_rec, async_mock.patch.object(
            test_module.OOBInvitationRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as mock_oob_invi_rec_retrieve:
            mock_oob_invi_rec_retrieve.side_effect = StorageNotFoundError()
            with self.assertRaises(DIDXManagerError) as context:
                await self.manager.receive_request(mock_request, receipt)
            assert "No record of invitation" in str(context.exception)

    async def test_receive_request_public_did_no_did_doc_attachment(self):
        mock_request = async_mock.MagicMock()
        mock_request.did = TestConfig.test_did
        mock_request.did_doc_attach = None

        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=True,
        )

        await self.session.wallet.create_local_did(seed=None, did=TestConfig.test_did)

        self.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            test_module, "ConnRecord", async_mock.MagicMock()
        ) as mock_conn_rec, async_mock.patch.object(
            test_module.OOBInvitationRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as mock_oob_invi_rec_retrieve:
            with self.assertRaises(DIDXManagerError) as context:
                await self.manager.receive_request(mock_request, receipt)
            assert "DID Doc attachment missing or has no data" in str(context.exception)

    async def test_receive_request_public_did_x_wrong_did(self):
        mock_request = async_mock.MagicMock()
        mock_request.did = TestConfig.test_did
        mock_request.did_doc_attach = async_mock.MagicMock(
            data=async_mock.MagicMock(
                verify=async_mock.CoroutineMock(return_value=True),
                signed=async_mock.MagicMock(
                    decode=async_mock.MagicMock(return_value="dummy-did-doc")
                ),
            )
        )

        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=True,
        )

        await self.session.wallet.create_local_did(seed=None, did=TestConfig.test_did)

        self.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            test_module, "ConnRecord", async_mock.MagicMock()
        ) as mock_conn_rec, async_mock.patch.object(
            test_module.OOBInvitationRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as mock_oob_invi_rec_retrieve, async_mock.patch.object(
            test_module.DIDDoc, "from_json", async_mock.MagicMock()
        ) as mock_did_doc_from_json:
            mock_did_doc_from_json.return_value = async_mock.MagicMock(did="wrong-did")
            with self.assertRaises(DIDXManagerError) as context:
                await self.manager.receive_request(mock_request, receipt)
            assert "does not match" in str(context.exception)

    async def test_receive_request_public_did_x_did_doc_attach_bad_sig(self):
        mock_request = async_mock.MagicMock()
        mock_request.did = TestConfig.test_did
        mock_request.did_doc_attach = async_mock.MagicMock(
            data=async_mock.MagicMock(
                verify=async_mock.CoroutineMock(return_value=False)
            )
        )

        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=True,
        )

        await self.session.wallet.create_local_did(seed=None, did=TestConfig.test_did)

        self.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            test_module, "ConnRecord", async_mock.MagicMock()
        ) as mock_conn_rec, async_mock.patch.object(
            test_module.OOBInvitationRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as mock_oob_invi_rec_retrieve:
            with self.assertRaises(DIDXManagerError) as context:
                await self.manager.receive_request(mock_request, receipt)
            assert "DID Doc signature failed" in str(context.exception)

    async def test_receive_request_public_did_no_public_invites(self):
        mock_request = async_mock.MagicMock()
        mock_request.did = TestConfig.test_did
        mock_request.did_doc_attach = async_mock.MagicMock(
            data=async_mock.MagicMock(
                verify=async_mock.CoroutineMock(return_value=True),
                signed=async_mock.MagicMock(
                    decode=async_mock.MagicMock(return_value="dummy-did-doc")
                ),
            )
        )

        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=True,
        )

        await self.session.wallet.create_local_did(seed=None, did=TestConfig.test_did)

        self.session.context.update_settings({"public_invites": False})
        with async_mock.patch.object(
            test_module, "ConnRecord", async_mock.MagicMock()
        ) as mock_conn_rec, async_mock.patch.object(
            test_module.OOBInvitationRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as mock_oob_invi_rec_retrieve, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_deco, async_mock.patch.object(
            test_module, "DIDXResponse", autospec=True
        ) as mock_response, async_mock.patch.object(
            self.manager, "create_did_document", async_mock.CoroutineMock()
        ) as mock_create_did_doc, async_mock.patch.object(
            test_module.DIDDoc, "from_json", async_mock.MagicMock()
        ) as mock_did_doc_from_json:
            mock_did_doc_from_json.return_value = async_mock.MagicMock(
                did=TestConfig.test_did
            )
            with self.assertRaises(DIDXManagerError) as context:
                await self.manager.receive_request(mock_request, receipt)
            assert "Public invitations are not enabled" in str(context.exception)

    async def test_receive_request_public_did_no_auto_accept(self):
        mock_request = async_mock.MagicMock()
        mock_request.did = TestConfig.test_did
        mock_request.did_doc_attach = async_mock.MagicMock(
            data=async_mock.MagicMock(
                verify=async_mock.CoroutineMock(return_value=True),
                signed=async_mock.MagicMock(
                    decode=async_mock.MagicMock(return_value="dummy-did-doc")
                ),
            )
        )

        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=True,
        )

        await self.session.wallet.create_local_did(seed=None, did=TestConfig.test_did)

        self.session.context.update_settings(
            {"public_invites": True, "debug.auto_accept_requests": False}
        )
        mock_conn_rec_state_request = ConnRecord.State.REQUEST
        with async_mock.patch.object(
            test_module, "ConnRecord", async_mock.MagicMock()
        ) as mock_conn_rec, async_mock.patch.object(
            test_module.OOBInvitationRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as mock_oob_invi_rec_retrieve, async_mock.patch.object(
            test_module, "DIDDoc", autospec=True
        ) as mock_did_doc, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_deco, async_mock.patch.object(
            test_module, "DIDXResponse", autospec=True
        ) as mock_response, async_mock.patch.object(
            self.manager, "create_did_document", async_mock.CoroutineMock()
        ) as mock_create_did_doc:
            mock_conn_rec.return_value = async_mock.MagicMock(
                accept=ConnRecord.ACCEPT_MANUAL,
                my_did=None,
                state=mock_conn_rec_state_request.rfc23,
                attach_request=async_mock.CoroutineMock(),
                retrieve_request=async_mock.CoroutineMock(),
                save=async_mock.CoroutineMock(),
            )
            mock_oob_invi_rec_retrieve.return_value = async_mock.MagicMock(
                auto_accept=False,
            )
            mock_did_doc.from_json = async_mock.MagicMock(
                return_value=async_mock.MagicMock(did=TestConfig.test_did)
            )
            conn_rec = await self.manager.receive_request(mock_request, receipt)
            assert conn_rec

        messages = self.responder.messages
        assert not messages

    async def test_receive_request_peer_did(self):
        mock_request = async_mock.MagicMock()
        mock_request.did = TestConfig.test_did
        mock_request.did_doc_attach = async_mock.MagicMock(
            data=async_mock.MagicMock(
                verify=async_mock.CoroutineMock(return_value=True),
                signed=async_mock.MagicMock(
                    decode=async_mock.MagicMock(return_value="dummy-did-doc")
                ),
            )
        )
        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            recipient_verkey=TestConfig.test_verkey,
        )
        mock_conn = async_mock.MagicMock(
            my_did=TestConfig.test_did,
            their_did=TestConfig.test_target_did,
            invitation_key=TestConfig.test_verkey,
            connection_id="dummy",
            is_multiuse_invitation=True,
            state=ConnRecord.State.INVITATION.rfc23,
            their_role=ConnRecord.Role.REQUESTER.rfc23,
            save=async_mock.CoroutineMock(),
            attach_request=async_mock.CoroutineMock(),
            accept=ConnRecord.ACCEPT_MANUAL,
            metadata_get_all=async_mock.CoroutineMock(return_value={"test": "value"}),
        )
        mock_conn_rec_state_request = ConnRecord.State.REQUEST

        await self.session.wallet.create_local_did(seed=None, did=TestConfig.test_did)

        self.session.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            test_module, "ConnRecord", async_mock.MagicMock()
        ) as mock_conn_rec, async_mock.patch.object(
            test_module.OOBInvitationRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as mock_oob_invi_rec_retrieve, async_mock.patch.object(
            test_module, "DIDDoc", autospec=True
        ) as mock_did_doc, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_deco, async_mock.patch.object(
            test_module, "DIDXResponse", autospec=True
        ) as mock_response:
            mock_conn_rec.retrieve_by_invitation_key = async_mock.CoroutineMock(
                return_value=mock_conn
            )
            mock_conn_rec.return_value = async_mock.MagicMock(
                accept=ConnRecord.ACCEPT_AUTO,
                my_did=None,
                state=mock_conn_rec_state_request.rfc23,
                attach_request=async_mock.CoroutineMock(),
                retrieve_request=async_mock.CoroutineMock(),
                save=async_mock.CoroutineMock(),
                metadata_set=async_mock.CoroutineMock(),
            )
            mock_oob_invi_rec_retrieve.return_value = async_mock.MagicMock(
                auto_accept=False,
            )
            mock_did_doc.from_json = async_mock.MagicMock(
                return_value=async_mock.MagicMock(did=TestConfig.test_did)
            )
            mock_attach_deco.from_indy_dict = async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    data=async_mock.MagicMock(sign=async_mock.CoroutineMock())
                )
            )
            mock_response.return_value = async_mock.MagicMock(
                assign_thread_from=async_mock.MagicMock(),
                assign_trace_from=async_mock.MagicMock(),
            )

            conn_rec = await self.manager.receive_request(mock_request, receipt)
            assert conn_rec
            mock_conn_rec.return_value.metadata_set.assert_called()

        assert not self.responder.messages

    async def test_receive_request_peer_did_not_found_x(self):
        mock_request = async_mock.MagicMock()
        mock_request.did = TestConfig.test_did
        mock_request.did_doc_attach = async_mock.MagicMock(
            data=async_mock.MagicMock(
                verify=async_mock.CoroutineMock(return_value=True),
                signed=async_mock.MagicMock(
                    decode=async_mock.MagicMock(return_value="dummy-did-doc")
                ),
            )
        )
        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            recipient_verkey=TestConfig.test_verkey,
        )

        await self.session.wallet.create_local_did(seed=None, did=TestConfig.test_did)

        with async_mock.patch.object(
            test_module, "ConnRecord", async_mock.MagicMock()
        ) as mock_conn_rec, async_mock.patch.object(
            test_module.OOBInvitationRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as mock_oob_invi_rec_retrieve:
            mock_conn_rec.retrieve_by_invitation_key = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )
            with self.assertRaises(DIDXManagerError):
                await self.manager.receive_request(mock_request, receipt)

    async def test_create_response(self):
        conn_rec = ConnRecord(
            connection_id="dummy", state=ConnRecord.State.REQUEST.rfc23
        )

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_request", async_mock.CoroutineMock()
        ) as mock_retrieve_req, async_mock.patch.object(
            conn_rec, "save", async_mock.CoroutineMock()
        ) as mock_save, async_mock.patch.object(
            test_module, "DIDDoc", autospec=True
        ) as mock_did_doc, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_deco, async_mock.patch.object(
            test_module, "DIDXResponse", autospec=True
        ) as mock_response, async_mock.patch.object(
            self.manager, "create_did_document", async_mock.CoroutineMock()
        ) as mock_create_did_doc:
            mock_create_did_doc.return_value = async_mock.MagicMock(
                serialize=async_mock.MagicMock()
            )
            mock_attach_deco.from_indy_dict = async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    data=async_mock.MagicMock(sign=async_mock.CoroutineMock())
                )
            )

            await self.manager.create_response(conn_rec, "http://10.20.30.40:5060/")

    async def test_create_response_conn_rec_my_did(self):
        conn_rec = ConnRecord(
            connection_id="dummy",
            my_did=TestConfig.test_did,
            state=ConnRecord.State.REQUEST.rfc23,
        )

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_request", async_mock.CoroutineMock()
        ) as mock_retrieve_req, async_mock.patch.object(
            conn_rec, "save", async_mock.CoroutineMock()
        ) as mock_save, async_mock.patch.object(
            test_module, "DIDDoc", autospec=True
        ) as mock_did_doc, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_deco, async_mock.patch.object(
            test_module, "DIDXResponse", autospec=True
        ) as mock_response, async_mock.patch.object(
            self.manager, "create_did_document", async_mock.CoroutineMock()
        ) as mock_create_did_doc, async_mock.patch.object(
            InMemoryWallet, "get_local_did", async_mock.CoroutineMock()
        ) as mock_get_loc_did:
            mock_get_loc_did.return_value = self.did_info
            mock_create_did_doc.return_value = async_mock.MagicMock(
                serialize=async_mock.MagicMock()
            )
            mock_attach_deco.from_indy_dict = async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    data=async_mock.MagicMock(sign=async_mock.CoroutineMock())
                )
            )

            await self.manager.create_response(conn_rec, "http://10.20.30.40:5060/")

    async def test_create_response_bad_state(self):
        with self.assertRaises(DIDXManagerError):
            await self.manager.create_response(
                ConnRecord(
                    invitation_key=TestConfig.test_verkey,
                    their_label="Hello",
                    their_role=ConnRecord.Role.REQUESTER.rfc23,
                    state=ConnRecord.State.ABANDONED.rfc23,
                    alias="Bob",
                )
            )

    async def test_accept_response_find_by_thread_id(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.did = TestConfig.test_target_did
        mock_response.did_doc_attach = async_mock.MagicMock(
            data=async_mock.MagicMock(
                verify=async_mock.CoroutineMock(return_value=True),
                signed=async_mock.MagicMock(
                    decode=async_mock.MagicMock(
                        return_value=json.dumps({"dummy": "did-doc"})
                    )
                ),
            )
        )

        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=True,
        )

        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id, async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_id, async_mock.patch.object(
            DIDDoc, "deserialize", async_mock.MagicMock()
        ) as mock_did_doc_deser:
            mock_did_doc_deser.return_value = async_mock.MagicMock(
                did=TestConfig.test_target_did
            )
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock(
                did=TestConfig.test_target_did,
                did_doc_attach=async_mock.MagicMock(
                    data=async_mock.MagicMock(
                        verify=async_mock.CoroutineMock(return_value=True),
                        signed=async_mock.MagicMock(
                            decode=async_mock.MagicMock(
                                return_value=json.dumps({"dummy": "did-doc"})
                            )
                        ),
                    )
                ),
                state=ConnRecord.State.REQUEST.rfc23,
                save=async_mock.CoroutineMock(),
            )
            mock_conn_retrieve_by_id.return_value = async_mock.MagicMock(
                their_did=TestConfig.test_target_did,
                save=async_mock.CoroutineMock(),
            )

            conn_rec = await self.manager.accept_response(mock_response, receipt)
            assert conn_rec.their_did == TestConfig.test_target_did
            assert ConnRecord.State.get(conn_rec.state) is ConnRecord.State.COMPLETED

    async def test_accept_response_not_found_by_thread_id_receipt_has_sender_did(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.did = TestConfig.test_target_did
        mock_response.did_doc_attach = async_mock.MagicMock(
            data=async_mock.MagicMock(
                verify=async_mock.CoroutineMock(return_value=True),
                signed=async_mock.MagicMock(
                    decode=async_mock.MagicMock(
                        return_value=json.dumps({"dummy": "did-doc"})
                    )
                ),
            )
        )

        receipt = MessageReceipt(sender_did=TestConfig.test_target_did)

        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id, async_mock.patch.object(
            ConnRecord, "retrieve_by_did", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_did, async_mock.patch.object(
            DIDDoc, "deserialize", async_mock.MagicMock()
        ) as mock_did_doc_deser:
            mock_did_doc_deser.return_value = async_mock.MagicMock(
                did=TestConfig.test_target_did
            )
            mock_conn_retrieve_by_req_id.side_effect = StorageNotFoundError()
            mock_conn_retrieve_by_did.return_value = async_mock.MagicMock(
                did=TestConfig.test_target_did,
                did_doc_attach=async_mock.MagicMock(
                    data=async_mock.MagicMock(
                        verify=async_mock.CoroutineMock(return_value=True),
                        signed=async_mock.MagicMock(
                            decode=async_mock.MagicMock(
                                return_value=json.dumps({"dummy": "did-doc"})
                            )
                        ),
                    )
                ),
                state=ConnRecord.State.REQUEST.rfc23,
                save=async_mock.CoroutineMock(),
            )

            conn_rec = await self.manager.accept_response(mock_response, receipt)
            assert conn_rec.their_did == TestConfig.test_target_did
            assert ConnRecord.State.get(conn_rec.state) is ConnRecord.State.COMPLETED

    async def test_accept_response_not_found_by_thread_id_nor_receipt_sender_did(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.did = TestConfig.test_target_did
        mock_response.did_doc_attach = async_mock.MagicMock(
            data=async_mock.MagicMock(
                verify=async_mock.CoroutineMock(return_value=True),
                signed=async_mock.MagicMock(
                    decode=async_mock.MagicMock(
                        return_value=json.dumps({"dummy": "did-doc"})
                    )
                ),
            )
        )

        receipt = MessageReceipt(sender_did=TestConfig.test_target_did)

        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id, async_mock.patch.object(
            ConnRecord, "retrieve_by_did", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_did:
            mock_conn_retrieve_by_req_id.side_effect = StorageNotFoundError()
            mock_conn_retrieve_by_did.side_effect = StorageNotFoundError()

            with self.assertRaises(DIDXManagerError):
                await self.manager.accept_response(mock_response, receipt)

    async def test_accept_response_find_by_thread_id_bad_state(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.did = TestConfig.test_target_did
        mock_response.did_doc_attach = async_mock.MagicMock(
            data=async_mock.MagicMock(
                verify=async_mock.CoroutineMock(return_value=True),
                signed=async_mock.MagicMock(
                    decode=async_mock.MagicMock(
                        return_value=json.dumps({"dummy": "did-doc"})
                    )
                ),
            )
        )

        receipt = MessageReceipt(sender_did=TestConfig.test_target_did)

        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id:
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock(
                state=ConnRecord.State.ABANDONED.rfc23
            )

            with self.assertRaises(DIDXManagerError):
                await self.manager.accept_response(mock_response, receipt)

    async def test_accept_response_find_by_thread_id_no_did_doc_attached(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.did = TestConfig.test_target_did
        mock_response.did_doc_attach = None

        receipt = MessageReceipt(sender_did=TestConfig.test_target_did)

        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id:
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock(
                did=TestConfig.test_target_did,
                did_doc_attach=async_mock.MagicMock(
                    data=async_mock.MagicMock(
                        verify=async_mock.CoroutineMock(return_value=True),
                        signed=async_mock.MagicMock(
                            decode=async_mock.MagicMock(
                                return_value=json.dumps({"dummy": "did-doc"})
                            )
                        ),
                    )
                ),
                state=ConnRecord.State.REQUEST.rfc23,
                save=async_mock.CoroutineMock(),
            )

            with self.assertRaises(DIDXManagerError):
                await self.manager.accept_response(mock_response, receipt)

    async def test_accept_response_find_by_thread_id_did_mismatch(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.did = TestConfig.test_target_did
        mock_response.did_doc_attach = async_mock.MagicMock(
            data=async_mock.MagicMock(
                verify=async_mock.CoroutineMock(return_value=True),
                signed=async_mock.MagicMock(
                    decode=async_mock.MagicMock(
                        return_value=json.dumps({"dummy": "did-doc"})
                    )
                ),
            )
        )

        receipt = MessageReceipt(sender_did=TestConfig.test_target_did)

        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id, async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_id, async_mock.patch.object(
            DIDDoc, "deserialize", async_mock.MagicMock()
        ) as mock_did_doc_deser:
            mock_did_doc_deser.return_value = async_mock.MagicMock(
                did=TestConfig.test_did
            )
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock(
                did=TestConfig.test_target_did,
                did_doc_attach=async_mock.MagicMock(
                    data=async_mock.MagicMock(
                        verify=async_mock.CoroutineMock(return_value=True),
                        signed=async_mock.MagicMock(
                            decode=async_mock.MagicMock(
                                return_value=json.dumps({"dummy": "did-doc"})
                            )
                        ),
                    )
                ),
                state=ConnRecord.State.REQUEST.rfc23,
                save=async_mock.CoroutineMock(),
            )
            mock_conn_retrieve_by_id.return_value = async_mock.MagicMock(
                their_did=TestConfig.test_target_did,
                save=async_mock.CoroutineMock(),
            )

            with self.assertRaises(DIDXManagerError):
                await self.manager.accept_response(mock_response, receipt)

    async def test_accept_complete(self):
        mock_complete = async_mock.MagicMock()
        receipt = MessageReceipt(sender_did=TestConfig.test_target_did)

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id:
            mock_conn_retrieve_by_req_id.return_value.save = async_mock.CoroutineMock()
            conn_rec = await self.manager.accept_complete(mock_complete, receipt)
            assert ConnRecord.State.get(conn_rec.state) is ConnRecord.State.COMPLETED

    async def test_accept_complete_x_not_found(self):
        mock_complete = async_mock.MagicMock()
        receipt = MessageReceipt(sender_did=TestConfig.test_target_did)

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id:
            mock_conn_retrieve_by_req_id.side_effect = StorageNotFoundError()
            with self.assertRaises(DIDXManagerError):
                await self.manager.accept_complete(mock_complete, receipt)

    async def test_create_did_document(self):
        did_info = DIDInfo(
            TestConfig.test_did,
            TestConfig.test_verkey,
            None,
        )

        mock_conn = async_mock.MagicMock(
            connection_id="dummy",
            inbound_connection_id=None,
            their_did=TestConfig.test_target_did,
            state=ConnRecord.State.COMPLETED.rfc23,
        )

        did_doc = self.make_did_doc(
            did=TestConfig.test_target_did,
            verkey=TestConfig.test_target_verkey,
        )
        for i in range(2):  # first cover store-record, then update-value
            await self.manager.store_did_document(did_doc)

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            did_doc = await self.manager.create_did_document(
                did_info=did_info,
                inbound_connection_id="dummy",
                svc_endpoints=[TestConfig.test_endpoint],
            )

    async def test_create_did_document_not_completed(self):
        did_info = DIDInfo(
            TestConfig.test_did,
            TestConfig.test_verkey,
            None,
        )

        mock_conn = async_mock.MagicMock(
            connection_id="dummy",
            inbound_connection_id=None,
            their_did=TestConfig.test_target_did,
            state=ConnRecord.State.ABANDONED.rfc23,
        )

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            with self.assertRaises(DIDXManagerError):
                await self.manager.create_did_document(
                    did_info=did_info,
                    inbound_connection_id="dummy",
                    svc_endpoints=[TestConfig.test_endpoint],
                )

    async def test_create_did_document_no_services(self):
        did_info = DIDInfo(
            TestConfig.test_did,
            TestConfig.test_verkey,
            None,
        )

        mock_conn = async_mock.MagicMock(
            connection_id="dummy",
            inbound_connection_id=None,
            their_did=TestConfig.test_target_did,
            state=ConnRecord.State.COMPLETED.rfc23,
        )

        x_did_doc = self.make_did_doc(
            did=TestConfig.test_target_did, verkey=TestConfig.test_target_verkey
        )
        x_did_doc._service = {}
        for i in range(2):  # first cover store-record, then update-value
            await self.manager.store_did_document(x_did_doc)

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            with self.assertRaises(DIDXManagerError):
                await self.manager.create_did_document(
                    did_info=did_info,
                    inbound_connection_id="dummy",
                    svc_endpoints=[TestConfig.test_endpoint],
                )

    async def test_create_did_document_no_service_endpoint(self):
        did_info = DIDInfo(
            TestConfig.test_did,
            TestConfig.test_verkey,
            None,
        )

        mock_conn = async_mock.MagicMock(
            connection_id="dummy",
            inbound_connection_id=None,
            their_did=TestConfig.test_target_did,
            state=ConnRecord.State.COMPLETED.rfc23,
        )

        x_did_doc = self.make_did_doc(
            did=TestConfig.test_target_did, verkey=TestConfig.test_target_verkey
        )
        x_did_doc._service = {}
        x_did_doc.set(
            Service(TestConfig.test_target_did, "dummy", "IndyAgent", [], [], "", 0)
        )
        for i in range(2):  # first cover store-record, then update-value
            await self.manager.store_did_document(x_did_doc)

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            with self.assertRaises(DIDXManagerError):
                await self.manager.create_did_document(
                    did_info=did_info,
                    inbound_connection_id="dummy",
                    svc_endpoints=[TestConfig.test_endpoint],
                )

    async def test_create_did_document_no_service_recip_keys(self):
        did_info = DIDInfo(
            TestConfig.test_did,
            TestConfig.test_verkey,
            None,
        )

        mock_conn = async_mock.MagicMock(
            connection_id="dummy",
            inbound_connection_id=None,
            their_did=TestConfig.test_target_did,
            state=ConnRecord.State.COMPLETED.rfc23,
        )

        x_did_doc = self.make_did_doc(
            did=TestConfig.test_target_did, verkey=TestConfig.test_target_verkey
        )
        x_did_doc._service = {}
        x_did_doc.set(
            Service(
                TestConfig.test_target_did,
                "dummy",
                "IndyAgent",
                [],
                [],
                TestConfig.test_endpoint,
                0,
            )
        )
        for i in range(2):  # first cover store-record, then update-value
            await self.manager.store_did_document(x_did_doc)

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            with self.assertRaises(DIDXManagerError):
                await self.manager.create_did_document(
                    did_info=did_info,
                    inbound_connection_id="dummy",
                    svc_endpoints=[TestConfig.test_endpoint],
                )

    async def test_did_key_storage(self):
        did_info = DIDInfo(
            TestConfig.test_did,
            TestConfig.test_verkey,
            None,
        )

        did_doc = self.make_did_doc(
            did=TestConfig.test_target_did, verkey=TestConfig.test_target_verkey
        )

        await self.manager.add_key_for_did(
            did=TestConfig.test_target_did, key=TestConfig.test_target_verkey
        )

        did = await self.manager.find_did_for_key(key=TestConfig.test_target_verkey)
        assert did == TestConfig.test_target_did
        await self.manager.remove_keys_for_did(TestConfig.test_target_did)

    async def test_diddoc_connection_targets_diddoc(self):
        did_doc = self.make_did_doc(
            TestConfig.test_target_did,
            TestConfig.test_target_verkey,
        )
        targets = self.manager.diddoc_connection_targets(
            did_doc,
            TestConfig.test_verkey,
        )
        assert isinstance(targets[0], ConnectionTarget)

    async def test_diddoc_connection_targets_diddoc_underspecified(self):
        with self.assertRaises(DIDXManagerError):
            self.manager.diddoc_connection_targets(None, TestConfig.test_verkey)

        x_did_doc = DIDDoc(did=None)
        with self.assertRaises(DIDXManagerError):
            self.manager.diddoc_connection_targets(x_did_doc, TestConfig.test_verkey)

        x_did_doc = self.make_did_doc(
            did=TestConfig.test_target_did, verkey=TestConfig.test_target_verkey
        )
        x_did_doc._service = {}
        with self.assertRaises(DIDXManagerError):
            self.manager.diddoc_connection_targets(x_did_doc, TestConfig.test_verkey)
