from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ....cache.base import BaseCache
from ....cache.basic import BasicCache
from ....config.base import InjectorError
from ....config.injection_context import InjectionContext
from ....connections.models.connection_record import ConnectionRecord
from ....connections.models.connection_target import ConnectionTarget
from ....connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from ....ledger.base import BaseLedger
from ....messaging.responder import BaseResponder, MockResponder
from ....storage.base import BaseStorage
from ....storage.basic import BasicStorage
from ....storage.error import StorageNotFoundError
from ....transport.inbound.receipt import MessageReceipt
from ....wallet.base import BaseWallet, DIDInfo
from ....wallet.basic import BasicWallet
from ....wallet.error import WalletNotFoundError

from ...routing.manager import RoutingManager

from ..manager import ConnectionManager, ConnectionManagerError
from ..messages.connection_invitation import ConnectionInvitation
from ..messages.connection_request import ConnectionRequest
from ..messages.connection_response import ConnectionResponse
from ..models.connection_detail import ConnectionDetail


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
            did, ident, pk_value, PublicKeyType.ED25519_SIG_2018, controller, False,
        )
        doc.set(pk)
        recip_keys = [pk]
        router_keys = []
        service = Service(
            did, "indy", "IndyAgent", recip_keys, router_keys, self.test_endpoint,
        )
        doc.set(service)
        return doc

class TestConnectionManager(AsyncTestCase, TestConfig):
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
        self.context.update_settings(
            {
                "default_endpoint": "http://aries.ca/endpoint",
                "default_label": "This guy",
                "additional_endpoints": [],
                "debug.auto_accept_invites": True,
                "debug.auto_accept_requests": True,
            }
        )


        self.manager = ConnectionManager(self.context)
        self.test_conn_rec = ConnectionRecord(
            my_did=self.test_did,
            their_did=self.test_target_did,
            their_role=None,
            state=ConnectionRecord.STATE_ACTIVE,
        )

    async def test_create_invitation_public_and_multi_use_fails(self):
        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            BaseWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, None,
            )
            with self.assertRaises(ConnectionManagerError):
                await self.manager.create_invitation(public=True, multi_use=True)

    async def test_create_invitation_non_multi_use_invitation_fails_on_reuse(self):
        connect_record, connect_invite = await self.manager.create_invitation()

        receipt = MessageReceipt(recipient_verkey=connect_record.invitation_key)

        requestA = ConnectionRequest(
            connection=ConnectionDetail(
                did=self.test_target_did,
                did_doc=self.make_did_doc(
                    self.test_target_did, self.test_target_verkey
                ),
            ),
            label="SameInviteRequestA",
        )

        await self.manager.receive_request(requestA, receipt)

        requestB = ConnectionRequest(
            connection=ConnectionDetail(
                did=self.test_did,
                did_doc=self.make_did_doc(self.test_did, self.test_verkey),
            ),
            label="SameInviteRequestB",
        )

        # requestB fails because the invitation was not set to multi-use
        rr_awaitable = self.manager.receive_request(requestB, receipt)
        await self.assertAsyncRaises(ConnectionManagerError, rr_awaitable)

    async def test_create_invitation_public(self):
        self.manager.context.update_settings({"public_invites": True})

        with async_mock.patch.object(
            BaseWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, None,
            )
            connect_record, connect_invite = await self.manager.create_invitation(
                public=True,
                my_endpoint="testendpoint"
            )

            assert connect_record == None
            assert connect_invite.did.endswith(self.test_did)

    async def test_create_invitation_public_no_public_invites(self):
        self.manager.context.update_settings({"public_invites": False})

        with self.assertRaises(ConnectionManagerError):
            await self.manager.create_invitation(
                public=True,
                my_endpoint="testendpoint"
            )

    async def test_create_invitation_public_no_public_did(self):
        self.manager.context.update_settings({"public_invites": True})

        with async_mock.patch.object(
            BaseWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = None
            with self.assertRaises(ConnectionManagerError):
                await self.manager.create_invitation(
                    public=True,
                    my_endpoint="testendpoint"
                )

    async def test_create_invitation_multi_use(self):
        connect_record, connect_invite = await self.manager.create_invitation(
            my_endpoint="testendpoint", multi_use=True
        )

        receipt = MessageReceipt(recipient_verkey=connect_record.invitation_key)

        requestA = ConnectionRequest(
            connection=ConnectionDetail(
                did=self.test_target_did,
                did_doc=self.make_did_doc(
                    self.test_target_did, self.test_target_verkey
                ),
            ),
            label="SameInviteRequestA",
        )

        await self.manager.receive_request(requestA, receipt)

        requestB = ConnectionRequest(
            connection=ConnectionDetail(
                did=self.test_did,
                did_doc=self.make_did_doc(self.test_did, self.test_verkey),
            ),
            label="SameInviteRequestB",
        )

        await self.manager.receive_request(requestB, receipt)

    async def test_receive_invitation(self):
        (_, connect_invite) = await self.manager.create_invitation(
            my_endpoint="testendpoint"
        )

        invitee_record = await self.manager.receive_invitation(connect_invite)
        assert invitee_record.state == ConnectionRecord.STATE_REQUEST

    async def test_receive_invitation_no_auto_accept(self):
        (_, connect_invite) = await self.manager.create_invitation(
            my_endpoint="testendpoint"
        )

        invitee_record = await self.manager.receive_invitation(
            connect_invite,
            accept=ConnectionRecord.ACCEPT_MANUAL)
        assert invitee_record.state == ConnectionRecord.STATE_INVITATION

    async def test_receive_invitation_bad_invitation(self):
        x_invites = [
            ConnectionInvitation(),
            ConnectionInvitation(
                recipient_keys=["3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"]
            )
        ]

        for x_invite in x_invites:
            with self.assertRaises(ConnectionManagerError):
                await self.manager.receive_invitation(x_invite)

    async def test_create_request(self):
        conn_req = await self.manager.create_request(
            ConnectionRecord(
                initiator=ConnectionRecord.INITIATOR_EXTERNAL,
                invitation_key=self.test_verkey,
                their_label="Hello",
                their_role="Point of contact",
                alias="Bob",
            )
        )
        assert conn_req

    async def test_create_request_my_endpoint(self):
        conn_req = await self.manager.create_request(
            ConnectionRecord(
                initiator=ConnectionRecord.INITIATOR_EXTERNAL,
                invitation_key=self.test_verkey,
                their_label="Hello",
                their_role="Point of contact",
                alias="Bob",
            ),
            my_endpoint="http://testendpoint.com/endpoint"
        )
        assert conn_req

    async def test_create_request_my_did(self):
        wallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=None,
            did=self.test_did
        )
        conn_req = await self.manager.create_request(
            ConnectionRecord(
                initiator=ConnectionRecord.INITIATOR_EXTERNAL,
                invitation_key=self.test_verkey,
                my_did=self.test_did,
                their_label="Hello",
                their_role="Point of contact",
                alias="Bob",
            )
        )
        assert conn_req

    async def test_receive_request_public_did(self):
        mock_request = async_mock.MagicMock()
        mock_request.connection = async_mock.MagicMock()
        mock_request.connection.did = self.test_did
        mock_request.connection.did_doc = async_mock.MagicMock()
        mock_request.connection.did_doc.did = self.test_did

        receipt = MessageReceipt(recipient_did=self.test_did, recipient_did_public=True)

        wallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=None,
            did=self.test_did
        )

        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnectionRecord, "attach_request", autospec=True
        ) as mock_conn_attach_request, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", autospec=True
        ) as mock_conn_retrieve_by_id, async_mock.patch.object(
            ConnectionRecord, "retrieve_request", autospec=True
        ):
            conn_rec = await self.manager.receive_request(mock_request, receipt)
            assert conn_rec

        messages = self.responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert type(result) == ConnectionResponse
        assert "connection_id" in target

    async def test_receive_request_public_did_no_did_doc(self):
        mock_request = async_mock.MagicMock()
        mock_request.connection = async_mock.MagicMock()
        mock_request.connection.did = self.test_did
        mock_request.connection.did_doc = None

        receipt = MessageReceipt(recipient_did=self.test_did, recipient_did_public=True)

        wallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=None,
            did=self.test_did
        )

        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnectionRecord, "attach_request", autospec=True
        ) as mock_conn_attach_request, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", autospec=True
        ) as mock_conn_retrieve_by_id, async_mock.patch.object(
            ConnectionRecord, "retrieve_request", autospec=True
        ):
            with self.assertRaises(ConnectionManagerError):
                await self.manager.receive_request(mock_request, receipt)

    async def test_receive_request_public_did_wrong_did(self):
        mock_request = async_mock.MagicMock()
        mock_request.connection = async_mock.MagicMock()
        mock_request.connection.did = self.test_did
        mock_request.connection.did_doc = async_mock.MagicMock()
        mock_request.connection.did_doc.did = "dummy"

        receipt = MessageReceipt(recipient_did=self.test_did, recipient_did_public=True)

        wallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=None,
            did=self.test_did
        )

        self.manager.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnectionRecord, "attach_request", autospec=True
        ) as mock_conn_attach_request, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", autospec=True
        ) as mock_conn_retrieve_by_id, async_mock.patch.object(
            ConnectionRecord, "retrieve_request", autospec=True
        ):
            with self.assertRaises(ConnectionManagerError):
                await self.manager.receive_request(mock_request, receipt)

    async def test_receive_request_public_did_no_public_invites(self):
        mock_request = async_mock.MagicMock()
        mock_request.connection = async_mock.MagicMock()
        mock_request.connection.did = self.test_did
        mock_request.connection.did_doc = async_mock.MagicMock()
        mock_request.connection.did_doc.did = self.test_did

        receipt = MessageReceipt(recipient_did=self.test_did, recipient_did_public=True)

        wallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=None,
            did=self.test_did
        )

        self.manager.context.update_settings({"public_invites": False})
        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnectionRecord, "attach_request", autospec=True
        ) as mock_conn_attach_request, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", autospec=True
        ) as mock_conn_retrieve_by_id, async_mock.patch.object(
            ConnectionRecord, "retrieve_request", autospec=True
        ):
            with self.assertRaises(ConnectionManagerError):
                await self.manager.receive_request(mock_request, receipt)

    async def test_receive_request_public_did_no_auto_accept(self):
        mock_request = async_mock.MagicMock()
        mock_request.connection = async_mock.MagicMock()
        mock_request.connection.did = self.test_did
        mock_request.connection.did_doc = async_mock.MagicMock()
        mock_request.connection.did_doc.did = self.test_did

        receipt = MessageReceipt(recipient_did=self.test_did, recipient_did_public=True)

        wallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=None,
            did=self.test_did
        )

        self.manager.context.update_settings(
            {"public_invites": True, "debug.auto_accept_requests": False}
        )
        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnectionRecord, "attach_request", autospec=True
        ) as mock_conn_attach_request, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", autospec=True
        ) as mock_conn_retrieve_by_id, async_mock.patch.object(
            ConnectionRecord, "retrieve_request", autospec=True
        ):
            conn_rec = await self.manager.receive_request(mock_request, receipt)
            assert conn_rec

        messages = self.responder.messages
        assert not messages

    async def test_create_response_bad_state(self):
        with self.assertRaises(ConnectionManagerError):
            await self.manager.create_response(
                ConnectionRecord(
                    initiator=ConnectionRecord.INITIATOR_EXTERNAL,
                    invitation_key=self.test_verkey,
                    their_label="Hello",
                    their_role="Point of contact",
                    alias="Bob",
                    state=ConnectionRecord.STATE_ERROR
                )
            )

    async def test_accept_response_find_by_thread_id(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.connection = async_mock.MagicMock()
        mock_response.connection.did = self.test_target_did
        mock_response.connection.did_doc = async_mock.MagicMock()
        mock_response.connection.did_doc.did = self.test_target_did

        receipt = MessageReceipt(recipient_did=self.test_did, recipient_did_public=True)

        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id:
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock()
            mock_conn_retrieve_by_req_id.return_value.did = self.test_target_did
            mock_conn_retrieve_by_req_id.return_value.did_doc = async_mock.MagicMock()
            mock_conn_retrieve_by_req_id.return_value.did_doc.did = (
                self.test_target_did
            )
            mock_conn_retrieve_by_req_id.return_value.state = (
                ConnectionRecord.STATE_RESPONSE
            )
            mock_conn_retrieve_by_req_id.return_value.save = async_mock.CoroutineMock()

            conn_rec = await self.manager.accept_response(mock_response, receipt)
            assert conn_rec.their_did == self.test_target_did
            assert conn_rec.state == ConnectionRecord.STATE_RESPONSE

    async def test_accept_response_not_found_by_thread_id_receipt_has_sender_did(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.connection = async_mock.MagicMock()
        mock_response.connection.did = self.test_target_did
        mock_response.connection.did_doc = async_mock.MagicMock()
        mock_response.connection.did_doc.did = self.test_target_did

        receipt = MessageReceipt(sender_did=self.test_target_did)

        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_did", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_did:
            mock_conn_retrieve_by_req_id.side_effect = StorageNotFoundError()
            mock_conn_retrieve_by_did.return_value = async_mock.MagicMock()
            mock_conn_retrieve_by_did.return_value.did = self.test_target_did
            mock_conn_retrieve_by_did.return_value.did_doc = async_mock.MagicMock()
            mock_conn_retrieve_by_did.return_value.did_doc.did = (
                self.test_target_did
            )
            mock_conn_retrieve_by_did.return_value.state = (
                ConnectionRecord.STATE_RESPONSE
            )
            mock_conn_retrieve_by_did.return_value.save = async_mock.CoroutineMock()

            conn_rec = await self.manager.accept_response(mock_response, receipt)
            assert conn_rec.their_did == self.test_target_did
            assert conn_rec.state == ConnectionRecord.STATE_RESPONSE

    async def test_accept_response_not_found_by_thread_id_nor_receipt_sender_did(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.connection = async_mock.MagicMock()
        mock_response.connection.did = self.test_target_did
        mock_response.connection.did_doc = async_mock.MagicMock()
        mock_response.connection.did_doc.did = self.test_target_did

        receipt = MessageReceipt(sender_did=self.test_target_did)

        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_did", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_did:
            mock_conn_retrieve_by_req_id.side_effect = StorageNotFoundError()
            mock_conn_retrieve_by_did.side_effect = StorageNotFoundError()

            with self.assertRaises(ConnectionManagerError):
                await self.manager.accept_response(mock_response, receipt)

    async def test_accept_response_find_by_thread_id_bad_state(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.connection = async_mock.MagicMock()
        mock_response.connection.did = self.test_target_did
        mock_response.connection.did_doc = async_mock.MagicMock()
        mock_response.connection.did_doc.did = self.test_target_did

        receipt = MessageReceipt(sender_did=self.test_target_did)

        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id:
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock()
            mock_conn_retrieve_by_req_id.return_value.state = (
                ConnectionRecord.STATE_ERROR
            )

            with self.assertRaises(ConnectionManagerError):
                await self.manager.accept_response(mock_response, receipt)

    async def test_accept_response_find_by_thread_id_no_connection_did_doc(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.connection = async_mock.MagicMock()
        mock_response.connection.did = self.test_target_did
        mock_response.connection.did_doc = None

        receipt = MessageReceipt(sender_did=self.test_target_did)

        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id:
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock()
            mock_conn_retrieve_by_req_id.return_value.did = self.test_target_did
            mock_conn_retrieve_by_req_id.return_value.did_doc = async_mock.MagicMock()
            mock_conn_retrieve_by_req_id.return_value.did_doc.did = (
                self.test_target_did
            )
            mock_conn_retrieve_by_req_id.return_value.state = (
                ConnectionRecord.STATE_RESPONSE
            )

            with self.assertRaises(ConnectionManagerError):
                await self.manager.accept_response(mock_response, receipt)

    async def test_accept_response_find_by_thread_id_did_mismatch(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.connection = async_mock.MagicMock()
        mock_response.connection.did = self.test_target_did
        mock_response.connection.did_doc = async_mock.MagicMock()
        mock_response.connection.did_doc.did = self.test_did

        receipt = MessageReceipt(sender_did=self.test_target_did)

        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id:
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock()
            mock_conn_retrieve_by_req_id.return_value.did = self.test_target_did
            mock_conn_retrieve_by_req_id.return_value.did_doc = async_mock.MagicMock()
            mock_conn_retrieve_by_req_id.return_value.did_doc.did = (
                self.test_target_did
            )
            mock_conn_retrieve_by_req_id.return_value.state = (
                ConnectionRecord.STATE_RESPONSE
            )

            with self.assertRaises(ConnectionManagerError):
                await self.manager.accept_response(mock_response, receipt)

    async def test_create_static_connection(self):
        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save:

            _my, _their, conn_rec = await self.manager.create_static_connection(
                my_did=self.test_did,
                their_did=self.test_target_did,
                their_verkey=self.test_target_verkey,
                their_endpoint=self.test_endpoint,
            )

            assert conn_rec.state == ConnectionRecord.STATE_ACTIVE

    async def test_create_static_connection_no_their(self):
        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save:

            with self.assertRaises(ConnectionManagerError):
                await self.manager.create_static_connection(
                    my_did=self.test_did,
                    their_did=None,
                    their_verkey=self.test_target_verkey,
                    their_endpoint=self.test_endpoint,
                )

    async def test_create_static_connection_their_seed_only(self):
        with async_mock.patch.object(
            ConnectionRecord, "save", autospec=True
        ) as mock_conn_rec_save:

            _my, _their, conn_rec = await self.manager.create_static_connection(
                my_did=self.test_did,
                their_seed=self.test_seed,
                their_endpoint=self.test_endpoint,
            )

            assert conn_rec.state == ConnectionRecord.STATE_ACTIVE

    async def test_find_connection_retrieve_by_did(self):
        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_did", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_did:
            mock_conn_retrieve_by_did.return_value = async_mock.MagicMock(
                state=ConnectionRecord.STATE_RESPONSE,
                save=async_mock.CoroutineMock()
            )

            conn_rec = await self.manager.find_connection(
                their_did=self.test_target_did,
                my_did=self.test_did,
                my_verkey=self.test_verkey,
                auto_complete=True,
            )
            assert conn_rec.state == ConnectionRecord.STATE_ACTIVE

    async def test_find_connection_retrieve_by_invitation_key(self):
        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_did", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_did, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_invitation_key", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_invitation_key:
            mock_conn_retrieve_by_did.side_effect = StorageNotFoundError()
            mock_conn_retrieve_by_invitation_key.return_value = async_mock.MagicMock(
                state=ConnectionRecord.STATE_RESPONSE,
                save=async_mock.CoroutineMock()
            )

            conn_rec = await self.manager.find_connection(
                their_did=self.test_target_did,
                my_did=self.test_did,
                my_verkey=self.test_verkey,
            )
            assert conn_rec

    async def test_find_connection_retrieve_by_did_inactive(self):
        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_did", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_did:
            mock_conn_retrieve_by_did.return_value = async_mock.MagicMock(
                state=ConnectionRecord.STATE_INACTIVE,
                save=async_mock.CoroutineMock()
            )

            conn_rec = await self.manager.find_connection(
                their_did=self.test_target_did,
                my_did=self.test_did,
                my_verkey=self.test_verkey,
                auto_complete=True,
            )
            assert conn_rec.state == ConnectionRecord.STATE_ACTIVE

    async def test_find_connection_retrieve_none_by_invitation_key(self):
        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_did", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_did, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_invitation_key", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_invitation_key:
            mock_conn_retrieve_by_did.side_effect = StorageNotFoundError()
            mock_conn_retrieve_by_invitation_key.side_effect = StorageNotFoundError()

            conn_rec = await self.manager.find_connection(
                their_did=self.test_target_did,
                my_did=self.test_did,
                my_verkey=self.test_verkey,
            )
            assert conn_rec is None

    async def test_find_inbound_connection(self):
        receipt = MessageReceipt(
            sender_verkey=self.test_verkey,
            recipient_verkey=self.test_target_verkey,
            recipient_did_public=False,
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.connection_id = "dummy"

        # First pass: not yet in cache
        with async_mock.patch.object(
            ConnectionManager, "resolve_inbound_connection", async_mock.CoroutineMock()
        ) as mock_conn_mgr_resolve_conn:
            mock_conn_mgr_resolve_conn.return_value = mock_conn

            conn_rec = await self.manager.find_inbound_connection(receipt)
            assert conn_rec

        # Second pass: in cache
        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            conn_rec = await self.manager.find_inbound_connection(receipt)
            assert conn_rec.id == mock_conn.id

    async def test_find_inbound_connection_no_cache(self):
        receipt = MessageReceipt(
            sender_verkey=self.test_verkey,
            recipient_verkey=self.test_target_verkey,
            recipient_did_public=False,
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.connection_id = "dummy"

        with async_mock.patch.object(
            self.manager.context, "inject", async_mock.CoroutineMock()
        ) as mock_ctx_inject, async_mock.patch.object(
            ConnectionManager, "resolve_inbound_connection", async_mock.CoroutineMock()
        ) as mock_conn_mgr_resolve_conn:
            mock_ctx_inject.return_value = None
            mock_conn_mgr_resolve_conn.return_value = mock_conn

            conn_rec = await self.manager.find_inbound_connection(receipt)
            assert conn_rec

    async def test_resolve_inbound_connection(self):
        receipt = MessageReceipt(
            sender_verkey=self.test_verkey,
            recipient_verkey=self.test_target_verkey,
            recipient_did_public=True,
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.connection_id = "dummy"

        with async_mock.patch.object(
            BasicWallet, "get_local_did_for_verkey", async_mock.CoroutineMock()
        ) as mock_wallet_get_local_did_for_verkey, async_mock.patch.object(
            self.manager, "find_connection", async_mock.CoroutineMock()
        ) as mock_mgr_find_conn:
            mock_wallet_get_local_did_for_verkey.return_value = DIDInfo(
                self.test_did, self.test_verkey, {"public": True},
            )
            mock_mgr_find_conn.return_value = mock_conn

            assert await self.manager.resolve_inbound_connection(receipt)

    async def test_resolve_inbound_connection_injector_error(self):
        receipt = MessageReceipt(
            sender_verkey=self.test_verkey,
            recipient_verkey=self.test_target_verkey,
            recipient_did_public=True,
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.connection_id = "dummy"

        with async_mock.patch.object(
            BasicWallet, "get_local_did_for_verkey", async_mock.CoroutineMock()
        ) as mock_wallet_get_local_did_for_verkey, async_mock.patch.object(
            self.manager, "find_connection", async_mock.CoroutineMock()
        ) as mock_mgr_find_conn:
            mock_wallet_get_local_did_for_verkey.side_effect = InjectorError()
            mock_mgr_find_conn.return_value = mock_conn

            assert await self.manager.resolve_inbound_connection(receipt)

    async def test_resolve_inbound_connection_wallet_not_found_error(self):
        receipt = MessageReceipt(
            sender_verkey=self.test_verkey,
            recipient_verkey=self.test_target_verkey,
            recipient_did_public=True,
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.connection_id = "dummy"

        with async_mock.patch.object(
            BasicWallet, "get_local_did_for_verkey", async_mock.CoroutineMock()
        ) as mock_wallet_get_local_did_for_verkey, async_mock.patch.object(
            self.manager, "find_connection", async_mock.CoroutineMock()
        ) as mock_mgr_find_conn:
            mock_wallet_get_local_did_for_verkey.side_effect = WalletNotFoundError()
            mock_mgr_find_conn.return_value = mock_conn

            assert await self.manager.resolve_inbound_connection(receipt)

    async def test_create_did_document(self):
        did_info = DIDInfo(
            self.test_did, self.test_verkey, None,
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.connection_id = "dummy"
        mock_conn.inbound_connection_id = None
        mock_conn.their_did = self.test_target_did
        mock_conn.state = ConnectionRecord.STATE_ACTIVE

        did_doc = self.make_did_doc(
            did=self.test_target_did,
            verkey=self.test_target_verkey
        )
        for i in range(2):  # first cover store-record, then update-value
            await self.manager.store_did_document(did_doc)

        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            did_doc = await self.manager.create_did_document(
                did_info=did_info,
                inbound_connection_id="dummy",
                svc_endpoints=[self.test_endpoint]
            )

    async def test_create_did_document_not_active(self):
        did_info = DIDInfo(
            self.test_did, self.test_verkey, None,
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.connection_id = "dummy"
        mock_conn.inbound_connection_id = None
        mock_conn.their_did = self.test_target_did
        mock_conn.state = ConnectionRecord.STATE_INACTIVE

        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            with self.assertRaises(ConnectionManagerError):
                await self.manager.create_did_document(
                    did_info=did_info,
                    inbound_connection_id="dummy",
                    svc_endpoints=[self.test_endpoint]
                )

    async def test_create_did_document_no_services(self):
        did_info = DIDInfo(
            self.test_did, self.test_verkey, None,
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.connection_id = "dummy"
        mock_conn.inbound_connection_id = None
        mock_conn.their_did = self.test_target_did
        mock_conn.state = ConnectionRecord.STATE_ACTIVE

        x_did_doc = self.make_did_doc(
            did=self.test_target_did,
            verkey=self.test_target_verkey
        )
        x_did_doc._service = {}
        for i in range(2):  # first cover store-record, then update-value
            await self.manager.store_did_document(x_did_doc)

        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            with self.assertRaises(ConnectionManagerError):
                await self.manager.create_did_document(
                    did_info=did_info,
                    inbound_connection_id="dummy",
                    svc_endpoints=[self.test_endpoint]
                )

    async def test_create_did_document_no_service_endpoint(self):
        did_info = DIDInfo(
            self.test_did, self.test_verkey, None,
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.connection_id = "dummy"
        mock_conn.inbound_connection_id = None
        mock_conn.their_did = self.test_target_did
        mock_conn.state = ConnectionRecord.STATE_ACTIVE

        x_did_doc = self.make_did_doc(
            did=self.test_target_did,
            verkey=self.test_target_verkey
        )
        x_did_doc._service = {}
        x_did_doc.set(
            Service(
                self.test_target_did,
                "dummy",
                "IndyAgent",
                [],
                [],
                "",
                0
            )
        )
        for i in range(2):  # first cover store-record, then update-value
            await self.manager.store_did_document(x_did_doc)

        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            with self.assertRaises(ConnectionManagerError):
                await self.manager.create_did_document(
                    did_info=did_info,
                    inbound_connection_id="dummy",
                    svc_endpoints=[self.test_endpoint]
                )

    async def test_create_did_document_no_service_recip_keys(self):
        did_info = DIDInfo(
            self.test_did, self.test_verkey, None,
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.connection_id = "dummy"
        mock_conn.inbound_connection_id = None
        mock_conn.their_did = self.test_target_did
        mock_conn.state = ConnectionRecord.STATE_ACTIVE

        x_did_doc = self.make_did_doc(
            did=self.test_target_did,
            verkey=self.test_target_verkey
        )
        x_did_doc._service = {}
        x_did_doc.set(
            Service(
                self.test_target_did,
                "dummy",
                "IndyAgent",
                [],
                [],
                self.test_endpoint,
                0
            )
        )
        for i in range(2):  # first cover store-record, then update-value
            await self.manager.store_did_document(x_did_doc)

        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            with self.assertRaises(ConnectionManagerError):
                await self.manager.create_did_document(
                    did_info=did_info,
                    inbound_connection_id="dummy",
                    svc_endpoints=[self.test_endpoint]
                )

    async def test_did_key_storage(self):
        did_info = DIDInfo(
            self.test_did, self.test_verkey, None,
        )

        did_doc = self.make_did_doc(
            did=self.test_target_did,
            verkey=self.test_target_verkey
        )

        await self.manager.add_key_for_did(
            did=self.test_target_did,
            key=self.test_target_verkey
        )

        did = await self.manager.find_did_for_key(key=self.test_target_verkey)
        assert did == self.test_target_did
        await self.manager.remove_keys_for_did(self.test_target_did)

    async def test_get_connection_targets_invitation_no_did(self):
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=self.test_seed, did=self.test_did, metadata=None
        )

        did_doc = self.make_did_doc(
            did=self.test_target_did,
            verkey=self.test_target_verkey
        )
        await self.manager.store_did_document(did_doc)

        # First pass: not yet in cache
        mock_conn = async_mock.MagicMock()
        mock_conn.my_did = self.test_did
        mock_conn.their_did = self.test_target_did
        mock_conn.connection_id = "dummy"
        mock_conn.state = ConnectionRecord.STATE_INVITATION
        mock_conn.initiator = ConnectionRecord.INITIATOR_EXTERNAL

        mock_invite = async_mock.MagicMock()
        mock_invite.did = None
        mock_invite.endpoint = self.test_endpoint
        mock_invite.recipient_keys = [self.test_target_verkey]
        mock_invite.routing_keys = [self.test_verkey]
        mock_invite.label = "label"
        mock_conn.retrieve_invitation = async_mock.CoroutineMock(
            return_value=mock_invite
        )

        targets = await self.manager.get_connection_targets(
            connection_id=None,
            connection=mock_conn,
        )
        assert len(targets) == 1
        target = targets[0]
        assert target.did == mock_conn.their_did
        assert target.endpoint == mock_invite.endpoint
        assert target.label == mock_invite.label
        assert target.recipient_keys == mock_invite.recipient_keys
        assert target.routing_keys == mock_invite.routing_keys
        assert target.sender_key == (await wallet.get_local_did(self.test_did)).verkey

        # Next pass: exercise cache
        targets = await self.manager.get_connection_targets(
            connection_id=None,
            connection=mock_conn,
        )
        assert len(targets) == 1
        target = targets[0]
        assert target.did == mock_conn.their_did
        assert target.endpoint == mock_invite.endpoint
        assert target.label == mock_invite.label
        assert target.recipient_keys == mock_invite.recipient_keys
        assert target.routing_keys == mock_invite.routing_keys
        assert target.sender_key == (await wallet.get_local_did(self.test_did)).verkey

    async def test_get_connection_targets_retrieve_connection(self):
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=self.test_seed, did=self.test_did, metadata=None
        )

        did_doc = self.make_did_doc(
            did=self.test_target_did,
            verkey=self.test_target_verkey
        )
        await self.manager.store_did_document(did_doc)

        # Connection target not in cache
        mock_conn = async_mock.MagicMock()
        mock_conn.my_did = self.test_did
        mock_conn.their_did = self.test_target_did
        mock_conn.connection_id = "dummy"
        mock_conn.state = ConnectionRecord.STATE_INVITATION
        mock_conn.initiator = ConnectionRecord.INITIATOR_EXTERNAL

        mock_invite = async_mock.MagicMock()
        mock_invite.did = None
        mock_invite.endpoint = self.test_endpoint
        mock_invite.recipient_keys = [self.test_target_verkey]
        mock_invite.routing_keys = [self.test_verkey]
        mock_invite.label = "label"
        mock_conn.retrieve_invitation = async_mock.CoroutineMock(
            return_value=mock_invite
        )

        with async_mock.patch.object(
            ConnectionTarget, "serialize", autospec=True
        ) as mock_conn_target_ser, async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn
            mock_conn_target_ser.return_value = {"serialized": "value"}
            targets = await self.manager.get_connection_targets(
                connection_id="dummy",
                connection=None,
            )
            assert len(targets) == 1
            target = targets[0]
            assert target.did == mock_conn.their_did
            assert target.endpoint == mock_invite.endpoint
            assert target.label == mock_invite.label
            assert target.recipient_keys == mock_invite.recipient_keys
            assert target.routing_keys == mock_invite.routing_keys
            assert target.sender_key == (await wallet.get_local_did(self.test_did)).verkey

    async def test_get_connection_targets_no_cache(self):
        self.context.injector.clear_binding(BaseCache)
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=self.test_seed, did=self.test_did, metadata=None
        )

        did_doc = self.make_did_doc(
            did=self.test_target_did,
            verkey=self.test_target_verkey
        )
        await self.manager.store_did_document(did_doc)

        mock_conn = async_mock.MagicMock()
        mock_conn.my_did = self.test_did
        mock_conn.their_did = self.test_target_did
        mock_conn.connection_id = "dummy"
        mock_conn.state = ConnectionRecord.STATE_INVITATION
        mock_conn.initiator = ConnectionRecord.INITIATOR_EXTERNAL

        mock_invite = async_mock.MagicMock()
        mock_invite.did = None
        mock_invite.endpoint = self.test_endpoint
        mock_invite.recipient_keys = [self.test_target_verkey]
        mock_invite.routing_keys = [self.test_verkey]
        mock_invite.label = "label"
        mock_conn.retrieve_invitation = async_mock.CoroutineMock(
            return_value=mock_invite
        )

        targets = await self.manager.get_connection_targets(
            connection_id=None,
            connection=mock_conn,
        )
        assert len(targets) == 1
        target = targets[0]
        assert target.did == mock_conn.their_did
        assert target.endpoint == mock_invite.endpoint
        assert target.label == mock_invite.label
        assert target.recipient_keys == mock_invite.recipient_keys
        assert target.routing_keys == mock_invite.routing_keys
        assert target.sender_key == (await wallet.get_local_did(self.test_did)).verkey

    async def test_fetch_connection_targets_no_my_did(self):
        mock_conn = async_mock.MagicMock()
        mock_conn.my_did = None
        assert await self.manager.fetch_connection_targets(mock_conn) is None

    async def test_fetch_connection_targets_invitation_did_no_ledger(self):
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=self.test_seed, did=self.test_did, metadata=None
        )

        mock_invite = async_mock.MagicMock()
        mock_invite.did = self.test_target_did
        mock_invite.endpoint = self.test_endpoint
        mock_invite.recipient_keys = [self.test_target_verkey]
        mock_invite.routing_keys = [self.test_verkey]
        mock_invite.label = "label"

        mock_conn = async_mock.MagicMock()
        mock_conn.my_did = self.test_did
        mock_conn.state = ConnectionRecord.STATE_INVITATION
        mock_conn.initiator = ConnectionRecord.INITIATOR_EXTERNAL
        mock_conn.retrieve_invitation = async_mock.CoroutineMock(
            return_value=mock_invite
        )

        with self.assertRaises(ConnectionManagerError):
            await self.manager.fetch_connection_targets(mock_conn)

    async def test_fetch_connection_targets_invitation_did_ledger(self):
        self.ledger = async_mock.MagicMock()
        self.ledger.get_endpoint_for_did = async_mock.CoroutineMock(
            return_value=self.test_endpoint
        )
        self.ledger.get_key_for_did = async_mock.CoroutineMock(
            return_value=self.test_target_verkey
        )
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=self.test_seed, did=self.test_did, metadata=None
        )

        mock_invite = async_mock.MagicMock()
        mock_invite.did = self.test_target_did
        mock_invite.endpoint = self.test_endpoint
        mock_invite.recipient_keys = [self.test_target_verkey]
        mock_invite.routing_keys = [self.test_verkey]
        mock_invite.label = "label"

        mock_conn = async_mock.MagicMock()
        mock_conn.my_did = self.test_did
        mock_conn.their_did = self.test_target_did
        mock_conn.state = ConnectionRecord.STATE_INVITATION
        mock_conn.initiator = ConnectionRecord.INITIATOR_EXTERNAL
        mock_conn.retrieve_invitation = async_mock.CoroutineMock(
            return_value=mock_invite
        )

        targets = await self.manager.fetch_connection_targets(mock_conn)
        assert len(targets) == 1
        target = targets[0]
        assert target.did == mock_conn.their_did
        assert target.endpoint == mock_invite.endpoint
        assert target.label == mock_invite.label
        assert target.recipient_keys == mock_invite.recipient_keys
        assert target.routing_keys == []
        assert target.sender_key == (await wallet.get_local_did(self.test_did)).verkey

    async def test_fetch_connection_targets_conn_initiator_multi_no_their_did(self):
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=self.test_seed, did=self.test_did, metadata=None
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.my_did = self.test_did
        mock_conn.their_did = None
        mock_conn.initiator = ConnectionRecord.INITIATOR_MULTIUSE
        assert await self.manager.fetch_connection_targets(mock_conn) is None

    async def test_fetch_connection_targets_conn_initiator_multi_their_did(self):
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=self.test_seed, did=self.test_did, metadata=None
        )

        did_doc = self.make_did_doc(
            did=self.test_did,
            verkey=self.test_verkey
        )
        await self.manager.store_did_document(did_doc)

        mock_conn = async_mock.MagicMock()
        mock_conn.my_did = self.test_did
        mock_conn.their_did = self.test_did
        mock_conn.their_label = "self-connection formalism"
        mock_conn.initiator = ConnectionRecord.INITIATOR_MULTIUSE

        targets = await self.manager.fetch_connection_targets(mock_conn)
        assert len(targets) == 1
        target = targets[0]
        assert target.did == mock_conn.their_did
        assert target.endpoint == self.test_endpoint
        assert target.label == mock_conn.their_label
        assert target.recipient_keys == [self.test_verkey]
        assert target.routing_keys == []
        assert target.sender_key == (await wallet.get_local_did(self.test_did)).verkey

    async def test_diddoc_connection_targets_diddoc_underspecified(self):
        with self.assertRaises(ConnectionManagerError):
            self.manager.diddoc_connection_targets(None, self.test_verkey)

        x_did_doc = DIDDoc(did=None)
        with self.assertRaises(ConnectionManagerError):
            self.manager.diddoc_connection_targets(x_did_doc, self.test_verkey)

        x_did_doc = self.make_did_doc(
            did=self.test_target_did,
            verkey=self.test_target_verkey
        )
        x_did_doc._service = {}
        with self.assertRaises(ConnectionManagerError):
            self.manager.diddoc_connection_targets(x_did_doc, self.test_verkey)

    async def test_establish_inbound(self):
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=self.test_seed, did=self.test_did, metadata=None
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.my_did = self.test_did
        mock_conn.is_ready = True
        mock_conn.save = async_mock.CoroutineMock()

        inbound_conn_id = "dummy"
        
        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            RoutingManager, "send_create_route", async_mock.CoroutineMock()
        ) as mock_routing_mgr_send_create_route:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            state = await self.manager.establish_inbound(
                mock_conn,
                inbound_conn_id,
                None
            )
            assert state == ConnectionRecord.ROUTING_STATE_REQUEST

    async def test_establish_inbound_conn_rec_no_my_did(self):
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=self.test_seed, did=self.test_did, metadata=None
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.my_did = None
        mock_conn.is_ready = True
        mock_conn.save = async_mock.CoroutineMock()

        inbound_conn_id = "dummy"
        
        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            RoutingManager, "send_create_route", async_mock.CoroutineMock()
        ) as mock_routing_mgr_send_create_route:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            state = await self.manager.establish_inbound(
                mock_conn,
                inbound_conn_id,
                None
            )
            assert state == ConnectionRecord.ROUTING_STATE_REQUEST

    async def test_establish_inbound_no_conn_record(self):
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=self.test_seed, did=self.test_did, metadata=None
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.my_did = self.test_did
        mock_conn.is_ready = True
        mock_conn.save = async_mock.CoroutineMock()

        inbound_conn_id = "dummy"
        
        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            RoutingManager, "send_create_route", async_mock.CoroutineMock()
        ) as mock_routing_mgr_send_create_route:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(ConnectionManagerError):
                await self.manager.establish_inbound(
                    mock_conn,
                    inbound_conn_id,
                    None
                )

    async def test_establish_inbound_router_not_ready(self):
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await wallet.create_local_did(
            seed=self.test_seed, did=self.test_did, metadata=None
        )

        mock_conn = async_mock.MagicMock()
        mock_conn.my_did = self.test_did
        mock_conn.is_ready = False
        mock_conn.save = async_mock.CoroutineMock()

        inbound_conn_id = "dummy"
        
        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            RoutingManager, "send_create_route", async_mock.CoroutineMock()
        ) as mock_routing_mgr_send_create_route:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            with self.assertRaises(ConnectionManagerError):
                await self.manager.establish_inbound(
                    mock_conn,
                    inbound_conn_id,
                    None
                )

    async def test_update_inbound(self):
        with async_mock.patch.object(
            ConnectionRecord, "query", async_mock.CoroutineMock()
        ) as mock_conn_rec_query, async_mock.patch.object(
            self.wallet, "get_local_did", autospec=True
        ) as mock_wallet_get_local_did:
            mock_conn_rec_query.return_value = [
                async_mock.MagicMock(
                    my_did=None,
                    their_did=self.test_target_did,
                    their_role=None,
                    save=None,
                ),
                async_mock.MagicMock(
                    my_did=self.test_did,
                    their_did=self.test_target_did,
                    their_role=None,
                    save=async_mock.CoroutineMock(),
                ),
            ]
            mock_wallet_get_local_did.return_value = async_mock.CoroutineMock(
                verkey=self.test_verkey
            )
            await self.manager.update_inbound(
                "dummy",
                self.test_verkey,
                ConnectionRecord.STATE_ACTIVE
            )
            mock_conn_rec_query.return_value[1].save.assert_called_once_with(
                self.context
            )
