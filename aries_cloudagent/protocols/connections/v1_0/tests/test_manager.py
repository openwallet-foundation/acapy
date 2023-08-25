from unittest.mock import call

from asynctest import TestCase as AsyncTestCase, mock as async_mock
from multiformats import multibase, multicodec
from pydid import DIDDocument, DIDDocumentBuilder
from pydid.verification_method import (
    Ed25519VerificationKey2018,
    Ed25519VerificationKey2020,
    JsonWebKey2020,
)

from .. import manager as test_module
from .....cache.base import BaseCache
from .....cache.in_memory import InMemoryCache
from .....config.base import InjectionError
from .....connections.base_manager import BaseConnectionManagerError
from .....connections.models.conn_record import ConnRecord
from .....connections.models.connection_target import ConnectionTarget
from .....connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from .....core.in_memory import InMemoryProfile
from .....core.oob_processor import OobMessageProcessor
from .....core.profile import ProfileSession
from .....did.did_key import DIDKey
from .....messaging.responder import BaseResponder, MockResponder
from .....multitenant.base import BaseMultitenantManager
from .....multitenant.manager import MultitenantManager
from .....protocols.routing.v1_0.manager import RoutingManager
from .....resolver.default.legacy_peer import LegacyPeerDIDResolver
from .....resolver.did_resolver import DIDResolver
from .....storage.error import StorageNotFoundError
from .....transport.inbound.receipt import MessageReceipt
from .....wallet.base import DIDInfo
from .....wallet.did_method import DIDMethods, SOV
from .....wallet.error import WalletNotFoundError
from .....wallet.in_memory import InMemoryWallet
from .....wallet.key_type import ED25519
from .....wallet.util import b58_to_bytes, bytes_to_b64
from ....coordinate_mediation.v1_0.manager import MediationManager
from ....coordinate_mediation.v1_0.messages.mediate_request import MediationRequest
from ....coordinate_mediation.v1_0.models.mediation_record import MediationRecord
from ....coordinate_mediation.v1_0.route_manager import RouteManager
from ....discovery.v2_0.manager import V20DiscoveryMgr
from ..manager import ConnectionManager, ConnectionManagerError
from ..messages.connection_invitation import ConnectionInvitation
from ..messages.connection_request import ConnectionRequest
from ..messages.connection_response import ConnectionResponse
from ..models.connection_detail import ConnectionDetail


class TestConnectionManager(AsyncTestCase):
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

    async def setUp(self):
        self.test_seed = "testseed000000000000000000000001"
        self.test_did = "55GkHamhTU1ZbTbV2ab9DE"
        self.test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
        self.test_endpoint = "http://localhost"

        self.test_target_did = "GbuDUYXaUZRfHD2jeDuQuP"
        self.test_target_verkey = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"

        self.responder = MockResponder()

        self.oob_mock = async_mock.MagicMock(
            clean_finished_oob_record=async_mock.CoroutineMock(return_value=None)
        )
        self.route_manager = async_mock.MagicMock(RouteManager)
        self.route_manager.routing_info = async_mock.CoroutineMock(
            return_value=([], self.test_endpoint)
        )
        self.route_manager.mediation_record_if_id = async_mock.CoroutineMock(
            return_value=None
        )
        self.resolver = DIDResolver()
        self.resolver.register_resolver(LegacyPeerDIDResolver())

        self.profile = InMemoryProfile.test_profile(
            {
                "default_endpoint": "http://aries.ca/endpoint",
                "default_label": "This guy",
                "additional_endpoints": ["http://aries.ca/another-endpoint"],
                "debug.auto_accept_invites": True,
                "debug.auto_accept_requests": True,
            },
            bind={
                BaseResponder: self.responder,
                BaseCache: InMemoryCache(),
                OobMessageProcessor: self.oob_mock,
                RouteManager: self.route_manager,
                DIDMethods: DIDMethods(),
                DIDResolver: self.resolver,
            },
        )
        self.context = self.profile.context

        self.multitenant_mgr = async_mock.MagicMock(MultitenantManager, autospec=True)
        self.context.injector.bind_instance(
            BaseMultitenantManager, self.multitenant_mgr
        )

        self.test_mediator_routing_keys = [
            "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRR"
        ]
        self.test_mediator_conn_id = "mediator-conn-id"
        self.test_mediator_endpoint = "http://mediator.example.com"

        self.manager = ConnectionManager(self.profile)
        assert self.manager.profile

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
        self.context.update_settings({"public_invites": True})

        self.route_manager.route_verkey = async_mock.CoroutineMock()
        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )
            connect_record, connect_invite = await self.manager.create_invitation(
                public=True, my_endpoint="testendpoint"
            )

            assert connect_record
            assert connect_invite.did.endswith(self.test_did)
            self.route_manager.route_verkey.assert_called_once_with(
                self.profile, self.test_verkey
            )

    async def test_create_invitation_public_no_public_invites(self):
        self.context.update_settings({"public_invites": False})

        with self.assertRaises(ConnectionManagerError):
            await self.manager.create_invitation(
                public=True, my_endpoint="testendpoint"
            )

    async def test_create_invitation_public_no_public_did(self):
        self.context.update_settings({"public_invites": True})

        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = None
            with self.assertRaises(ConnectionManagerError):
                await self.manager.create_invitation(
                    public=True, my_endpoint="testendpoint"
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

    async def test_create_invitation_recipient_routing_endpoint(self):
        async with self.profile.session() as session:
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )
            connect_record, connect_invite = await self.manager.create_invitation(
                my_endpoint=self.test_endpoint,
                recipient_keys=[self.test_verkey],
                routing_keys=[self.test_verkey],
            )

            receipt = MessageReceipt(recipient_verkey=connect_record.invitation_key)

            requestA = ConnectionRequest(
                connection=ConnectionDetail(
                    did=self.test_target_did,
                    did_doc=self.make_did_doc(
                        self.test_target_did, self.test_target_verkey
                    ),
                ),
                label="InviteRequestA",
            )

            await self.manager.receive_request(requestA, receipt)

    async def test_create_invitation_metadata_assigned(self):
        async with self.profile.session() as session:
            record, invite = await self.manager.create_invitation(
                metadata={"hello": "world"}
            )

            assert await record.metadata_get_all(session) == {"hello": "world"}

    async def test_create_invitation_multi_use_metadata_transfers_to_connection(self):
        async with self.profile.session() as session:
            connect_record, _ = await self.manager.create_invitation(
                my_endpoint="testendpoint", multi_use=True, metadata={"test": "value"}
            )

            receipt = MessageReceipt(recipient_verkey=connect_record.invitation_key)

            request = ConnectionRequest(
                connection=ConnectionDetail(
                    did=self.test_target_did,
                    did_doc=self.make_did_doc(
                        self.test_target_did, self.test_target_verkey
                    ),
                ),
                label="request",
            )

            new_conn_rec = await self.manager.receive_request(request, receipt)
            assert new_conn_rec != connect_record
            assert await new_conn_rec.metadata_get_all(session) == {"test": "value"}

    async def test_create_invitation_mediation_overwrites_routing_and_endpoint(self):
        self.route_manager.routing_info = async_mock.CoroutineMock(
            return_value=(self.test_mediator_routing_keys, self.test_mediator_endpoint)
        )
        async with self.profile.session() as session:
            mediation_record = MediationRecord(
                role=MediationRecord.ROLE_CLIENT,
                state=MediationRecord.STATE_GRANTED,
                connection_id=self.test_mediator_conn_id,
                routing_keys=self.test_mediator_routing_keys,
                endpoint=self.test_mediator_endpoint,
            )
            await mediation_record.save(session)
            with async_mock.patch.object(
                MediationManager,
                "get_default_mediator",
            ) as mock_get_default_mediator:
                _, invite = await self.manager.create_invitation(
                    routing_keys=[self.test_verkey],
                    my_endpoint=self.test_endpoint,
                    mediation_id=mediation_record.mediation_id,
                )
                assert invite.routing_keys == self.test_mediator_routing_keys
                assert invite.endpoint == self.test_mediator_endpoint
                mock_get_default_mediator.assert_not_called()

    async def test_create_invitation_mediation_using_default(self):
        self.route_manager.routing_info = async_mock.CoroutineMock(
            return_value=(self.test_mediator_routing_keys, self.test_mediator_endpoint)
        )
        async with self.profile.session() as session:
            mediation_record = MediationRecord(
                role=MediationRecord.ROLE_CLIENT,
                state=MediationRecord.STATE_GRANTED,
                connection_id=self.test_mediator_conn_id,
                routing_keys=self.test_mediator_routing_keys,
                endpoint=self.test_mediator_endpoint,
            )
            await mediation_record.save(session)
            with async_mock.patch.object(
                self.route_manager,
                "mediation_record_if_id",
                async_mock.CoroutineMock(return_value=mediation_record),
            ):
                _, invite = await self.manager.create_invitation(
                    routing_keys=[self.test_verkey],
                    my_endpoint=self.test_endpoint,
                )
                assert invite.routing_keys == self.test_mediator_routing_keys
                assert invite.endpoint == self.test_mediator_endpoint
                self.route_manager.routing_info.assert_awaited_once_with(
                    self.profile, self.test_endpoint, mediation_record
                )

    async def test_receive_invitation(self):
        (_, connect_invite) = await self.manager.create_invitation(
            my_endpoint="testendpoint"
        )

        invitee_record = await self.manager.receive_invitation(connect_invite)
        assert ConnRecord.State.get(invitee_record.state) is ConnRecord.State.REQUEST

    async def test_receive_invitation_no_auto_accept(self):
        (_, connect_invite) = await self.manager.create_invitation(
            my_endpoint="testendpoint"
        )

        invitee_record = await self.manager.receive_invitation(
            connect_invite, auto_accept=False
        )
        assert ConnRecord.State.get(invitee_record.state) is ConnRecord.State.INVITATION

    async def test_receive_invitation_bad_invitation(self):
        x_invites = [
            ConnectionInvitation(),
            ConnectionInvitation(
                recipient_keys=["3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"]
            ),
        ]

        for x_invite in x_invites:
            with self.assertRaises(ConnectionManagerError):
                await self.manager.receive_invitation(x_invite)

    async def test_receive_invitation_with_did(self):
        """Test invitation received with a public DID instead of service info."""
        invite = ConnectionInvitation(did=self.test_did)
        invitee_record = await self.manager.receive_invitation(invite)
        assert ConnRecord.State.get(invitee_record.state) is ConnRecord.State.REQUEST

    async def test_receive_invitation_mediation_passes_id_when_auto_accept(self):
        with async_mock.patch.object(
            ConnectionManager, "create_request"
        ) as create_request:
            record, connect_invite = await self.manager.create_invitation(
                my_endpoint="testendpoint"
            )

            invitee_record = await self.manager.receive_invitation(
                connect_invite, mediation_id="test-mediation-id", auto_accept=True
            )
            create_request.assert_called_once_with(
                invitee_record, mediation_id="test-mediation-id"
            )

    async def test_create_request(self):
        conn_req = await self.manager.create_request(
            ConnRecord(
                invitation_key=self.test_verkey,
                their_label="Hello",
                their_role=ConnRecord.Role.RESPONDER.rfc160,
                alias="Bob",
            )
        )
        assert conn_req

    async def test_create_request_my_endpoint(self):
        conn_req = await self.manager.create_request(
            ConnRecord(
                invitation_key=self.test_verkey,
                their_label="Hello",
                their_role=ConnRecord.Role.RESPONDER.rfc160,
                alias="Bob",
            ),
            my_endpoint="http://testendpoint.com/endpoint",
        )
        assert conn_req

    async def test_create_request_my_did(self):
        async with self.profile.session() as session:
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=None,
                did=self.test_did,
            )
            conn_req = await self.manager.create_request(
                ConnRecord(
                    invitation_key=self.test_verkey,
                    my_did=self.test_did,
                    their_label="Hello",
                    their_role=ConnRecord.Role.RESPONDER.rfc160,
                    alias="Bob",
                )
            )
            assert conn_req

    async def test_create_request_multitenant(self):
        self.context.update_settings(
            {"wallet.id": "test_wallet", "multitenant.enabled": True}
        )
        mediation_record = MediationRecord(
            role=MediationRecord.ROLE_CLIENT,
            state=MediationRecord.STATE_GRANTED,
            connection_id=self.test_mediator_conn_id,
            routing_keys=self.test_mediator_routing_keys,
            endpoint=self.test_mediator_endpoint,
        )

        with async_mock.patch.object(
            InMemoryWallet, "create_local_did", autospec=True
        ) as mock_wallet_create_local_did, async_mock.patch.object(
            self.multitenant_mgr,
            "get_default_mediator",
            async_mock.CoroutineMock(return_value=mediation_record),
        ), async_mock.patch.object(
            ConnectionManager, "create_did_document", autospec=True
        ) as create_did_document, async_mock.patch.object(
            self.route_manager,
            "mediation_record_for_connection",
            async_mock.CoroutineMock(return_value=None),
        ):
            mock_wallet_create_local_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )
            await self.manager.create_request(
                ConnRecord(
                    invitation_key=self.test_verkey,
                    their_label="Hello",
                    their_role=ConnRecord.Role.RESPONDER.rfc160,
                    alias="Bob",
                ),
                my_endpoint=self.test_endpoint,
            )
            create_did_document.assert_called_once_with(
                self.manager,
                mock_wallet_create_local_did.return_value,
                None,
                [self.test_endpoint],
                mediation_records=[mediation_record],
            )
            self.route_manager.route_connection_as_invitee.assert_called_once()

    async def test_create_request_mediation_id(self):
        mediation_record = MediationRecord(
            role=MediationRecord.ROLE_CLIENT,
            state=MediationRecord.STATE_GRANTED,
            connection_id=self.test_mediator_conn_id,
            routing_keys=self.test_mediator_routing_keys,
            endpoint=self.test_mediator_endpoint,
        )

        record = ConnRecord(
            invitation_key=self.test_verkey,
            their_label="Hello",
            their_role=ConnRecord.Role.RESPONDER.rfc160,
            alias="Bob",
        )

        # Ensure the path with new did creation is hit
        record.my_did = None

        with async_mock.patch.object(
            ConnectionManager, "create_did_document", autospec=True
        ) as create_did_document, async_mock.patch.object(
            InMemoryWallet, "create_local_did"
        ) as create_local_did, async_mock.patch.object(
            self.route_manager,
            "mediation_record_for_connection",
            async_mock.CoroutineMock(return_value=mediation_record),
        ):
            did_info = DIDInfo(
                did=self.test_did,
                verkey=self.test_verkey,
                metadata={},
                method=SOV,
                key_type=ED25519,
            )
            create_local_did.return_value = did_info
            await self.manager.create_request(
                record,
                mediation_id=mediation_record.mediation_id,
                my_endpoint=self.test_endpoint,
            )
            create_local_did.assert_called_once_with(SOV, ED25519)
            create_did_document.assert_called_once_with(
                self.manager,
                did_info,
                None,
                [self.test_endpoint],
                mediation_records=[mediation_record],
            )

    async def test_create_request_default_mediator(self):
        async with self.profile.session() as session:
            mediation_record = MediationRecord(
                role=MediationRecord.ROLE_CLIENT,
                state=MediationRecord.STATE_GRANTED,
                connection_id=self.test_mediator_conn_id,
                routing_keys=self.test_mediator_routing_keys,
                endpoint=self.test_mediator_endpoint,
            )
            await mediation_record.save(session)

            record = ConnRecord(
                invitation_key=self.test_verkey,
                their_label="Hello",
                their_role=ConnRecord.Role.RESPONDER.rfc160,
                alias="Bob",
            )

            # Ensure the path with new did creation is hit
            record.my_did = None

            with async_mock.patch.object(
                ConnectionManager, "create_did_document", autospec=True
            ) as create_did_document, async_mock.patch.object(
                InMemoryWallet, "create_local_did"
            ) as create_local_did, async_mock.patch.object(
                self.route_manager,
                "mediation_record_for_connection",
                async_mock.CoroutineMock(return_value=mediation_record),
            ):
                did_info = DIDInfo(
                    did=self.test_did,
                    verkey=self.test_verkey,
                    metadata={},
                    method=SOV,
                    key_type=ED25519,
                )
                create_local_did.return_value = did_info
                await self.manager.create_request(
                    record,
                    my_endpoint=self.test_endpoint,
                )
                create_local_did.assert_called_once_with(SOV, ED25519)
                create_did_document.assert_called_once_with(
                    self.manager,
                    did_info,
                    None,
                    [self.test_endpoint],
                    mediation_records=[mediation_record],
                )

    async def test_receive_request_public_did_oob_invite(self):
        async with self.profile.session() as session:
            mock_request = async_mock.MagicMock()
            mock_request.connection = async_mock.MagicMock()
            mock_request.connection.did = self.test_did
            mock_request.connection.did_doc = async_mock.MagicMock()
            mock_request.connection.did_doc.did = self.test_did

            receipt = MessageReceipt(
                recipient_did=self.test_did, recipient_did_public=True
            )
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=None,
                did=self.test_did,
            )

            self.context.update_settings({"public_invites": True})
            with async_mock.patch.object(
                ConnRecord, "connection_id", autospec=True
            ), async_mock.patch.object(
                ConnRecord, "save", autospec=True
            ) as mock_conn_rec_save, async_mock.patch.object(
                ConnRecord, "attach_request", autospec=True
            ) as mock_conn_attach_request, async_mock.patch.object(
                ConnRecord, "retrieve_by_id", autospec=True
            ) as mock_conn_retrieve_by_id, async_mock.patch.object(
                ConnRecord, "retrieve_request", autospec=True
            ), async_mock.patch.object(
                ConnRecord, "retrieve_by_invitation_msg_id", async_mock.CoroutineMock()
            ) as mock_conn_retrieve_by_invitation_msg_id:
                mock_conn_retrieve_by_invitation_msg_id.return_value = ConnRecord()
                conn_rec = await self.manager.receive_request(mock_request, receipt)
                assert conn_rec

                self.oob_mock.clean_finished_oob_record.assert_called_once_with(
                    self.profile, mock_request
                )

    async def test_receive_request_public_did_unsolicited_fails(self):
        async with self.profile.session() as session:
            mock_request = async_mock.MagicMock()
            mock_request.connection = async_mock.MagicMock()
            mock_request.connection.did = self.test_did
            mock_request.connection.did_doc = async_mock.MagicMock()
            mock_request.connection.did_doc.did = self.test_did

            receipt = MessageReceipt(
                recipient_did=self.test_did, recipient_did_public=True
            )
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=None,
                did=self.test_did,
            )

            self.context.update_settings({"public_invites": True})
            with self.assertRaises(ConnectionManagerError), async_mock.patch.object(
                ConnRecord, "connection_id", autospec=True
            ), async_mock.patch.object(
                ConnRecord, "save", autospec=True
            ) as mock_conn_rec_save, async_mock.patch.object(
                ConnRecord, "attach_request", autospec=True
            ) as mock_conn_attach_request, async_mock.patch.object(
                ConnRecord, "retrieve_by_id", autospec=True
            ) as mock_conn_retrieve_by_id, async_mock.patch.object(
                ConnRecord, "retrieve_request", autospec=True
            ), async_mock.patch.object(
                ConnRecord, "retrieve_by_invitation_msg_id", async_mock.CoroutineMock()
            ) as mock_conn_retrieve_by_invitation_msg_id:
                mock_conn_retrieve_by_invitation_msg_id.return_value = None
                conn_rec = await self.manager.receive_request(mock_request, receipt)

    async def test_receive_request_public_did_conn_invite(self):
        async with self.profile.session() as session:
            mock_request = async_mock.MagicMock()
            mock_request.connection = async_mock.MagicMock()
            mock_request.connection.did = self.test_did
            mock_request.connection.did_doc = async_mock.MagicMock()
            mock_request.connection.did_doc.did = self.test_did

            receipt = MessageReceipt(
                recipient_did=self.test_did, recipient_did_public=True
            )
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=None,
                did=self.test_did,
            )

            mock_connection_record = async_mock.MagicMock()
            mock_connection_record.save = async_mock.CoroutineMock()
            mock_connection_record.attach_request = async_mock.CoroutineMock()

            self.context.update_settings({"public_invites": True})
            with async_mock.patch.object(
                ConnRecord, "connection_id", autospec=True
            ), async_mock.patch.object(
                ConnRecord, "save", autospec=True
            ) as mock_conn_rec_save, async_mock.patch.object(
                ConnRecord, "attach_request", autospec=True
            ) as mock_conn_attach_request, async_mock.patch.object(
                ConnRecord, "retrieve_by_id", autospec=True
            ) as mock_conn_retrieve_by_id, async_mock.patch.object(
                ConnRecord, "retrieve_request", autospec=True
            ), async_mock.patch.object(
                ConnRecord,
                "retrieve_by_invitation_msg_id",
                async_mock.CoroutineMock(return_value=mock_connection_record),
            ) as mock_conn_retrieve_by_invitation_msg_id:
                conn_rec = await self.manager.receive_request(mock_request, receipt)
                assert conn_rec

    async def test_receive_request_public_did_unsolicited(self):
        async with self.profile.session() as session:
            mock_request = async_mock.MagicMock()
            mock_request.connection = async_mock.MagicMock()
            mock_request.connection.did = self.test_did
            mock_request.connection.did_doc = async_mock.MagicMock()
            mock_request.connection.did_doc.did = self.test_did

            receipt = MessageReceipt(
                recipient_did=self.test_did, recipient_did_public=True
            )
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=None,
                did=self.test_did,
            )

            self.context.update_settings({"public_invites": True})
            self.context.update_settings({"requests_through_public_did": True})
            with async_mock.patch.object(
                ConnRecord, "connection_id", autospec=True
            ), async_mock.patch.object(
                ConnRecord, "save", autospec=True
            ) as mock_conn_rec_save, async_mock.patch.object(
                ConnRecord, "attach_request", autospec=True
            ) as mock_conn_attach_request, async_mock.patch.object(
                ConnRecord, "retrieve_by_id", autospec=True
            ) as mock_conn_retrieve_by_id, async_mock.patch.object(
                ConnRecord, "retrieve_request", autospec=True
            ), async_mock.patch.object(
                ConnRecord, "retrieve_by_invitation_msg_id", async_mock.CoroutineMock()
            ) as mock_conn_retrieve_by_invitation_msg_id:
                mock_conn_retrieve_by_invitation_msg_id.return_value = None
                conn_rec = await self.manager.receive_request(mock_request, receipt)
                assert conn_rec

    async def test_receive_request_public_did_no_did_doc(self):
        async with self.profile.session() as session:
            mock_request = async_mock.MagicMock()
            mock_request.connection = async_mock.MagicMock()
            mock_request.connection.did = self.test_did
            mock_request.connection.did_doc = None

            receipt = MessageReceipt(
                recipient_did=self.test_did, recipient_did_public=True
            )
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=None,
                did=self.test_did,
            )

            self.context.update_settings({"public_invites": True})
            with async_mock.patch.object(
                ConnRecord, "save", autospec=True
            ) as mock_conn_rec_save, async_mock.patch.object(
                ConnRecord, "attach_request", autospec=True
            ) as mock_conn_attach_request, async_mock.patch.object(
                ConnRecord, "retrieve_by_id", autospec=True
            ) as mock_conn_retrieve_by_id, async_mock.patch.object(
                ConnRecord, "retrieve_request", autospec=True
            ):
                with self.assertRaises(ConnectionManagerError):
                    await self.manager.receive_request(mock_request, receipt)

    async def test_receive_request_public_did_wrong_did(self):
        async with self.profile.session() as session:
            mock_request = async_mock.MagicMock()
            mock_request.connection = async_mock.MagicMock()
            mock_request.connection.did = self.test_did
            mock_request.connection.did_doc = async_mock.MagicMock()
            mock_request.connection.did_doc.did = "dummy"

            receipt = MessageReceipt(
                recipient_did=self.test_did, recipient_did_public=True
            )
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=None,
                did=self.test_did,
            )

            self.context.update_settings({"public_invites": True})
            with async_mock.patch.object(
                ConnRecord, "save", autospec=True
            ) as mock_conn_rec_save, async_mock.patch.object(
                ConnRecord, "attach_request", autospec=True
            ) as mock_conn_attach_request, async_mock.patch.object(
                ConnRecord, "retrieve_by_id", autospec=True
            ) as mock_conn_retrieve_by_id, async_mock.patch.object(
                ConnRecord, "retrieve_request", autospec=True
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
        async with self.profile.session() as session:
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=None,
                did=self.test_did,
            )

        self.context.update_settings({"public_invites": False})
        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "attach_request", autospec=True
        ) as mock_conn_attach_request, async_mock.patch.object(
            ConnRecord, "retrieve_by_id", autospec=True
        ) as mock_conn_retrieve_by_id, async_mock.patch.object(
            ConnRecord, "retrieve_request", autospec=True
        ):
            with self.assertRaises(ConnectionManagerError):
                await self.manager.receive_request(mock_request, receipt)

    async def test_receive_request_public_did_no_auto_accept(self):
        async with self.profile.session() as session:
            mock_request = async_mock.MagicMock()
            mock_request.connection = async_mock.MagicMock()
            mock_request.connection.did = self.test_did
            mock_request.connection.did_doc = async_mock.MagicMock()
            mock_request.connection.did_doc.did = self.test_did

            receipt = MessageReceipt(
                recipient_did=self.test_did, recipient_did_public=True
            )
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=None,
                did=self.test_did,
            )

            self.context.update_settings(
                {"public_invites": True, "debug.auto_accept_requests": False}
            )
            with async_mock.patch.object(
                ConnRecord, "save", autospec=True
            ) as mock_conn_rec_save, async_mock.patch.object(
                ConnRecord, "attach_request", autospec=True
            ) as mock_conn_attach_request, async_mock.patch.object(
                ConnRecord, "retrieve_by_id", autospec=True
            ) as mock_conn_retrieve_by_id, async_mock.patch.object(
                ConnRecord, "retrieve_request", autospec=True
            ), async_mock.patch.object(
                ConnRecord, "retrieve_by_invitation_msg_id", async_mock.CoroutineMock()
            ) as mock_conn_retrieve_by_invitation_msg_id:
                mock_conn_retrieve_by_invitation_msg_id.return_value = ConnRecord()
                conn_rec = await self.manager.receive_request(mock_request, receipt)
                assert conn_rec

            messages = self.responder.messages
            assert not messages

    async def test_create_response(self):
        conn_rec = ConnRecord(state=ConnRecord.State.REQUEST.rfc160)

        with async_mock.patch.object(
            ConnRecord, "log_state", autospec=True
        ) as mock_conn_log_state, async_mock.patch.object(
            ConnRecord, "retrieve_request", autospec=True
        ) as mock_conn_retrieve_request, async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_save, async_mock.patch.object(
            ConnectionResponse, "sign_field", autospec=True
        ) as mock_sign, async_mock.patch.object(
            conn_rec, "metadata_get", async_mock.CoroutineMock()
        ):
            await self.manager.create_response(conn_rec, "http://10.20.30.40:5060/")

    async def test_create_response_multitenant(self):
        self.context.update_settings(
            {"wallet.id": "test_wallet", "multitenant.enabled": True}
        )

        mediation_record = MediationRecord(
            role=MediationRecord.ROLE_CLIENT,
            state=MediationRecord.STATE_GRANTED,
            connection_id=self.test_mediator_conn_id,
            routing_keys=self.test_mediator_routing_keys,
            endpoint=self.test_mediator_endpoint,
        )

        with async_mock.patch.object(
            ConnRecord, "log_state", autospec=True
        ), async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ), async_mock.patch.object(
            ConnRecord, "metadata_get", async_mock.CoroutineMock(return_value=False)
        ), async_mock.patch.object(
            self.route_manager,
            "mediation_record_for_connection",
            async_mock.CoroutineMock(return_value=mediation_record),
        ), async_mock.patch.object(
            ConnRecord, "retrieve_request", autospec=True
        ), async_mock.patch.object(
            ConnectionResponse, "sign_field", autospec=True
        ), async_mock.patch.object(
            InMemoryWallet, "create_local_did", autospec=True
        ) as mock_wallet_create_local_did, async_mock.patch.object(
            self.multitenant_mgr,
            "get_default_mediator",
            async_mock.CoroutineMock(return_value=mediation_record),
        ), async_mock.patch.object(
            ConnectionManager, "create_did_document", autospec=True
        ) as create_did_document, async_mock.patch.object(
            self.route_manager,
            "mediation_record_for_connection",
            async_mock.CoroutineMock(return_value=None),
        ):
            mock_wallet_create_local_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )
            await self.manager.create_response(
                ConnRecord(
                    state=ConnRecord.State.REQUEST,
                ),
                my_endpoint=self.test_endpoint,
            )
            create_did_document.assert_called_once_with(
                self.manager,
                mock_wallet_create_local_did.return_value,
                None,
                [self.test_endpoint],
                mediation_records=[mediation_record],
            )
            self.route_manager.route_connection_as_inviter.assert_called_once()

    async def test_create_response_bad_state(self):
        with self.assertRaises(ConnectionManagerError):
            await self.manager.create_response(
                ConnRecord(
                    invitation_key=self.test_verkey,
                    their_label="Hello",
                    their_role=ConnRecord.Role.RESPONDER.rfc160,
                    alias="Bob",
                    state=ConnRecord.State.ABANDONED.rfc160,
                )
            )

    async def test_create_response_mediation(self):
        mediation_record = MediationRecord(
            role=MediationRecord.ROLE_CLIENT,
            state=MediationRecord.STATE_GRANTED,
            connection_id=self.test_mediator_conn_id,
            routing_keys=self.test_mediator_routing_keys,
            endpoint=self.test_mediator_endpoint,
        )

        record = ConnRecord(
            connection_id="test-conn-id",
            invitation_key=self.test_verkey,
            their_label="Hello",
            their_role=ConnRecord.Role.RESPONDER.rfc160,
            alias="Bob",
            state=ConnRecord.State.REQUEST.rfc160,
        )

        # Ensure the path with new did creation is hit
        record.my_did = None

        with async_mock.patch.object(
            ConnRecord, "log_state", autospec=True
        ), async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ), async_mock.patch.object(
            record, "metadata_get", async_mock.CoroutineMock(return_value=False)
        ), async_mock.patch.object(
            ConnectionManager, "create_did_document", autospec=True
        ) as create_did_document, async_mock.patch.object(
            InMemoryWallet, "create_local_did"
        ) as create_local_did, async_mock.patch.object(
            self.route_manager,
            "mediation_record_for_connection",
            async_mock.CoroutineMock(return_value=mediation_record),
        ), async_mock.patch.object(
            record, "retrieve_request", autospec=True
        ), async_mock.patch.object(
            ConnectionResponse, "sign_field", autospec=True
        ):
            did_info = DIDInfo(
                did=self.test_did,
                verkey=self.test_verkey,
                metadata={},
                method=SOV,
                key_type=ED25519,
            )
            create_local_did.return_value = did_info
            await self.manager.create_response(
                record,
                mediation_id=mediation_record.mediation_id,
                my_endpoint=self.test_endpoint,
            )
            create_local_did.assert_called_once_with(SOV, ED25519)
            create_did_document.assert_called_once_with(
                self.manager,
                did_info,
                None,
                [self.test_endpoint],
                mediation_records=[mediation_record],
            )
            self.route_manager.route_connection_as_inviter.assert_called_once()

    async def test_create_response_auto_send_mediation_request(self):
        conn_rec = ConnRecord(
            state=ConnRecord.State.REQUEST.rfc160,
        )
        conn_rec.my_did = None

        with async_mock.patch.object(
            ConnRecord, "log_state", autospec=True
        ) as mock_conn_log_state, async_mock.patch.object(
            ConnRecord, "retrieve_request", autospec=True
        ) as mock_conn_retrieve_request, async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_save, async_mock.patch.object(
            ConnectionResponse, "sign_field", autospec=True
        ) as mock_sign, async_mock.patch.object(
            conn_rec, "metadata_get", async_mock.CoroutineMock(return_value=True)
        ):
            await self.manager.create_response(conn_rec)

        assert len(self.responder.messages) == 1
        message, target = self.responder.messages[0]
        assert isinstance(message, MediationRequest)
        assert target["connection_id"] == conn_rec.connection_id

    async def test_accept_response_find_by_thread_id(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.connection = async_mock.MagicMock()
        mock_response.connection.did = self.test_target_did
        mock_response.connection.did_doc = async_mock.MagicMock()
        mock_response.connection.did_doc.did = self.test_target_did
        mock_response.verify_signed_field = async_mock.CoroutineMock(
            return_value="sig_verkey"
        )
        receipt = MessageReceipt(recipient_did=self.test_did, recipient_did_public=True)

        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id, async_mock.patch.object(
            MediationManager, "get_default_mediator", async_mock.CoroutineMock()
        ):
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock(
                did=self.test_target_did,
                did_doc=async_mock.MagicMock(did=self.test_target_did),
                state=ConnRecord.State.RESPONSE.rfc23,
                save=async_mock.CoroutineMock(),
                metadata_get=async_mock.CoroutineMock(),
                connection_id="test-conn-id",
                invitation_key="test-invitation-key",
            )
            conn_rec = await self.manager.accept_response(mock_response, receipt)
            assert conn_rec.their_did == self.test_target_did
            assert ConnRecord.State.get(conn_rec.state) is ConnRecord.State.RESPONSE

    async def test_accept_response_not_found_by_thread_id_receipt_has_sender_did(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.connection = async_mock.MagicMock()
        mock_response.connection.did = self.test_target_did
        mock_response.connection.did_doc = async_mock.MagicMock()
        mock_response.connection.did_doc.did = self.test_target_did
        mock_response.verify_signed_field = async_mock.CoroutineMock(
            return_value="sig_verkey"
        )

        receipt = MessageReceipt(sender_did=self.test_target_did)

        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id, async_mock.patch.object(
            ConnRecord, "retrieve_by_did", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_did, async_mock.patch.object(
            MediationManager, "get_default_mediator", async_mock.CoroutineMock()
        ):
            mock_conn_retrieve_by_req_id.side_effect = StorageNotFoundError()
            mock_conn_retrieve_by_did.return_value = async_mock.MagicMock(
                did=self.test_target_did,
                did_doc=async_mock.MagicMock(did=self.test_target_did),
                state=ConnRecord.State.RESPONSE.rfc23,
                save=async_mock.CoroutineMock(),
                metadata_get=async_mock.CoroutineMock(return_value=False),
                connection_id="test-conn-id",
                invitation_key="test-invitation-id",
            )

            conn_rec = await self.manager.accept_response(mock_response, receipt)
            assert conn_rec.their_did == self.test_target_did
            assert ConnRecord.State.get(conn_rec.state) is ConnRecord.State.RESPONSE

            assert not self.responder.messages

    async def test_accept_response_not_found_by_thread_id_nor_receipt_sender_did(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.connection = async_mock.MagicMock()
        mock_response.connection.did = self.test_target_did
        mock_response.connection.did_doc = async_mock.MagicMock()
        mock_response.connection.did_doc.did = self.test_target_did

        receipt = MessageReceipt(sender_did=self.test_target_did)

        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id, async_mock.patch.object(
            ConnRecord, "retrieve_by_did", async_mock.CoroutineMock()
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
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id:
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock(
                state=ConnRecord.State.ABANDONED.rfc23
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
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id:
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock(
                did=self.test_target_did,
                did_doc=async_mock.MagicMock(did=self.test_target_did),
                state=ConnRecord.State.RESPONSE.rfc23,
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
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id:
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock(
                did=self.test_target_did,
                did_doc=async_mock.MagicMock(did=self.test_target_did),
                state=ConnRecord.State.RESPONSE.rfc23,
            )

            with self.assertRaises(ConnectionManagerError):
                await self.manager.accept_response(mock_response, receipt)

    async def test_accept_response_verify_invitation_key_sign_failure(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.connection = async_mock.MagicMock()
        mock_response.connection.did = self.test_target_did
        mock_response.connection.did_doc = async_mock.MagicMock()
        mock_response.connection.did_doc.did = self.test_target_did
        mock_response.verify_signed_field = async_mock.CoroutineMock(
            side_effect=ValueError
        )
        receipt = MessageReceipt(recipient_did=self.test_did, recipient_did_public=True)

        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id, async_mock.patch.object(
            MediationManager, "get_default_mediator", async_mock.CoroutineMock()
        ):
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock(
                did=self.test_target_did,
                did_doc=async_mock.MagicMock(did=self.test_target_did),
                state=ConnRecord.State.RESPONSE.rfc23,
                save=async_mock.CoroutineMock(),
                metadata_get=async_mock.CoroutineMock(),
                connection_id="test-conn-id",
                invitation_key="test-invitation-key",
            )
            with self.assertRaises(ConnectionManagerError):
                await self.manager.accept_response(mock_response, receipt)

    async def test_accept_response_auto_send_mediation_request(self):
        mock_response = async_mock.MagicMock()
        mock_response._thread = async_mock.MagicMock()
        mock_response.connection = async_mock.MagicMock()
        mock_response.connection.did = self.test_target_did
        mock_response.connection.did_doc = async_mock.MagicMock()
        mock_response.connection.did_doc.did = self.test_target_did
        mock_response.verify_signed_field = async_mock.CoroutineMock(
            return_value="sig_verkey"
        )
        receipt = MessageReceipt(recipient_did=self.test_did, recipient_did_public=True)

        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save, async_mock.patch.object(
            ConnRecord, "retrieve_by_request_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_req_id, async_mock.patch.object(
            MediationManager, "get_default_mediator", async_mock.CoroutineMock()
        ):
            mock_conn_retrieve_by_req_id.return_value = async_mock.MagicMock(
                did=self.test_target_did,
                did_doc=async_mock.MagicMock(did=self.test_target_did),
                state=ConnRecord.State.RESPONSE.rfc23,
                save=async_mock.CoroutineMock(),
                metadata_get=async_mock.CoroutineMock(return_value=True),
                connection_id="test-conn-id",
                invitation_key="test-invitation-key",
            )
            conn_rec = await self.manager.accept_response(mock_response, receipt)
            assert conn_rec.their_did == self.test_target_did
            assert ConnRecord.State.get(conn_rec.state) is ConnRecord.State.RESPONSE

            assert len(self.responder.messages) == 1
            message, target = self.responder.messages[0]
            assert isinstance(message, MediationRequest)
            assert target["connection_id"] == conn_rec.connection_id

    async def test_establish_inbound(self):
        async with self.profile.session() as session:
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            mock_conn = async_mock.MagicMock(
                my_did=self.test_did,
                is_ready=True,
                save=async_mock.CoroutineMock(),
            )

            inbound_conn_id = "dummy"

            with async_mock.patch.object(
                ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
                RoutingManager, "send_create_route", async_mock.CoroutineMock()
            ) as mock_routing_mgr_send_create_route:
                mock_conn_rec_retrieve_by_id.return_value = mock_conn

                routing_state = await self.manager.establish_inbound(
                    mock_conn, inbound_conn_id, None
                )
                assert routing_state == ConnRecord.ROUTING_STATE_REQUEST

    async def test_establish_inbound_conn_rec_no_my_did(self):
        async with self.profile.session() as session:
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            mock_conn = async_mock.MagicMock()
            mock_conn.my_did = None
            mock_conn.is_ready = True
            mock_conn.save = async_mock.CoroutineMock()

            inbound_conn_id = "dummy"

            with async_mock.patch.object(
                ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
                RoutingManager, "send_create_route", async_mock.CoroutineMock()
            ) as mock_routing_mgr_send_create_route:
                mock_conn_rec_retrieve_by_id.return_value = mock_conn

                routing_state = await self.manager.establish_inbound(
                    mock_conn, inbound_conn_id, None
                )
                assert routing_state == ConnRecord.ROUTING_STATE_REQUEST

    async def test_establish_inbound_no_conn_record(self):
        async with self.profile.session() as session:
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            mock_conn = async_mock.MagicMock()
            mock_conn.my_did = self.test_did
            mock_conn.is_ready = True
            mock_conn.save = async_mock.CoroutineMock()

            inbound_conn_id = "dummy"

            with async_mock.patch.object(
                ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
                RoutingManager, "send_create_route", async_mock.CoroutineMock()
            ) as mock_routing_mgr_send_create_route:
                mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

                with self.assertRaises(ConnectionManagerError):
                    await self.manager.establish_inbound(
                        mock_conn, inbound_conn_id, None
                    )

    async def test_establish_inbound_router_not_ready(self):
        async with self.profile.session() as session:
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            mock_conn = async_mock.MagicMock()
            mock_conn.my_did = self.test_did
            mock_conn.is_ready = False
            mock_conn.save = async_mock.CoroutineMock()

            inbound_conn_id = "dummy"

            with async_mock.patch.object(
                ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
                RoutingManager, "send_create_route", async_mock.CoroutineMock()
            ) as mock_routing_mgr_send_create_route:
                mock_conn_rec_retrieve_by_id.return_value = mock_conn

                with self.assertRaises(ConnectionManagerError):
                    await self.manager.establish_inbound(
                        mock_conn, inbound_conn_id, None
                    )

    async def test_update_inbound(self):
        with async_mock.patch.object(
            ConnRecord, "query", async_mock.CoroutineMock()
        ) as mock_conn_rec_query, async_mock.patch.object(
            InMemoryWallet, "get_local_did", autospec=True
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
                "dummy", self.test_verkey, ConnRecord.ROUTING_STATE_ACTIVE
            )
            mock_conn_rec_query.return_value[1].save.assert_called_once()
            assert isinstance(
                mock_conn_rec_query.return_value[1].save.call_args[0][0], ProfileSession
            )
