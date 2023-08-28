"""Test connections base manager."""

from unittest.mock import call

from asynctest import TestCase as AsyncTestCase, mock as async_mock
from multiformats import multibase, multicodec
from pydid import DID, DIDDocument, DIDDocumentBuilder
from pydid.doc.builder import ServiceBuilder
from pydid.verification_method import (
    EcdsaSecp256k1VerificationKey2019,
    Ed25519VerificationKey2018,
    Ed25519VerificationKey2020,
    JsonWebKey2020,
)

from .. import base_manager as test_module
from ...cache.base import BaseCache
from ...cache.in_memory import InMemoryCache
from ...config.base import InjectionError
from ...connections.base_manager import BaseConnectionManagerError
from ...connections.models.conn_record import ConnRecord
from ...connections.models.connection_target import ConnectionTarget
from ...connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from ...core.in_memory import InMemoryProfile
from ...core.oob_processor import OobMessageProcessor
from ...did.did_key import DIDKey
from ...messaging.responder import BaseResponder, MockResponder
from ...multitenant.base import BaseMultitenantManager
from ...multitenant.manager import MultitenantManager
from ...protocols.connections.v1_0.messages.connection_invitation import (
    ConnectionInvitation,
)
from ...protocols.coordinate_mediation.v1_0.models.mediation_record import (
    MediationRecord,
)
from ...protocols.coordinate_mediation.v1_0.route_manager import RouteManager
from ...protocols.discovery.v2_0.manager import V20DiscoveryMgr
from ...resolver.default.key import KeyDIDResolver
from ...resolver.default.legacy_peer import LegacyPeerDIDResolver
from ...resolver.did_resolver import DIDResolver
from ...storage.base import BaseStorage
from ...storage.error import StorageNotFoundError
from ...storage.record import StorageRecord
from ...transport.inbound.receipt import MessageReceipt
from ...wallet.base import DIDInfo
from ...wallet.did_method import DIDMethods, SOV
from ...wallet.error import WalletNotFoundError
from ...wallet.in_memory import InMemoryWallet
from ...wallet.key_type import ED25519
from ...wallet.util import b58_to_bytes, bytes_to_b64
from ..base_manager import BaseConnectionManager


class TestBaseConnectionManager(AsyncTestCase):
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
        self.resolver.register_resolver(KeyDIDResolver())

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

        self.manager = BaseConnectionManager(self.profile)
        assert self.manager._profile

    async def test_create_did_document(self):
        did_info = DIDInfo(
            self.test_did,
            self.test_verkey,
            None,
            method=SOV,
            key_type=ED25519,
        )

        mock_conn = async_mock.MagicMock(
            connection_id="dummy",
            inbound_connection_id=None,
            their_did=self.test_target_did,
            state=ConnRecord.State.COMPLETED.rfc23,
        )

        did_doc = self.make_did_doc(
            did=self.test_target_did, verkey=self.test_target_verkey
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
                svc_endpoints=[self.test_endpoint],
            )

    async def test_create_did_document_not_active(self):
        did_info = DIDInfo(
            self.test_did,
            self.test_verkey,
            None,
            method=SOV,
            key_type=ED25519,
        )

        mock_conn = async_mock.MagicMock(
            connection_id="dummy",
            inbound_connection_id=None,
            their_did=self.test_target_did,
            state=ConnRecord.State.ABANDONED.rfc23,
        )

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            with self.assertRaises(BaseConnectionManagerError):
                await self.manager.create_did_document(
                    did_info=did_info,
                    inbound_connection_id="dummy",
                    svc_endpoints=[self.test_endpoint],
                )

    async def test_create_did_document_no_services(self):
        did_info = DIDInfo(
            self.test_did,
            self.test_verkey,
            None,
            method=SOV,
            key_type=ED25519,
        )

        mock_conn = async_mock.MagicMock(
            connection_id="dummy",
            inbound_connection_id=None,
            their_did=self.test_target_did,
            state=ConnRecord.State.COMPLETED.rfc23,
        )

        x_did_doc = self.make_did_doc(
            did=self.test_target_did, verkey=self.test_target_verkey
        )
        x_did_doc._service = {}
        for i in range(2):  # first cover store-record, then update-value
            await self.manager.store_did_document(x_did_doc)

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            with self.assertRaises(BaseConnectionManagerError):
                await self.manager.create_did_document(
                    did_info=did_info,
                    inbound_connection_id="dummy",
                    svc_endpoints=[self.test_endpoint],
                )

    async def test_create_did_document_no_service_endpoint(self):
        did_info = DIDInfo(
            self.test_did,
            self.test_verkey,
            None,
            method=SOV,
            key_type=ED25519,
        )

        mock_conn = async_mock.MagicMock(
            connection_id="dummy",
            inbound_connection_id=None,
            their_did=self.test_target_did,
            state=ConnRecord.State.COMPLETED.rfc23,
        )

        x_did_doc = self.make_did_doc(
            did=self.test_target_did, verkey=self.test_target_verkey
        )
        x_did_doc._service = {}
        x_did_doc.set(
            Service(self.test_target_did, "dummy", "IndyAgent", [], [], "", 0)
        )
        for i in range(2):  # first cover store-record, then update-value
            await self.manager.store_did_document(x_did_doc)

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            with self.assertRaises(BaseConnectionManagerError):
                await self.manager.create_did_document(
                    did_info=did_info,
                    inbound_connection_id="dummy",
                    svc_endpoints=[self.test_endpoint],
                )

    async def test_create_did_document_no_service_recip_keys(self):
        did_info = DIDInfo(
            self.test_did,
            self.test_verkey,
            None,
            method=SOV,
            key_type=ED25519,
        )

        mock_conn = async_mock.MagicMock(
            connection_id="dummy",
            inbound_connection_id=None,
            their_did=self.test_target_did,
            state=ConnRecord.State.COMPLETED.rfc23,
        )

        x_did_doc = self.make_did_doc(
            did=self.test_target_did, verkey=self.test_target_verkey
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
                0,
            )
        )
        for i in range(2):  # first cover store-record, then update-value
            await self.manager.store_did_document(x_did_doc)

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn

            with self.assertRaises(BaseConnectionManagerError):
                await self.manager.create_did_document(
                    did_info=did_info,
                    inbound_connection_id="dummy",
                    svc_endpoints=[self.test_endpoint],
                )

    async def test_create_did_document_mediation(self):
        did_info = DIDInfo(
            self.test_did,
            self.test_verkey,
            None,
            method=SOV,
            key_type=ED25519,
        )
        mediation_record = MediationRecord(
            role=MediationRecord.ROLE_CLIENT,
            state=MediationRecord.STATE_GRANTED,
            connection_id=self.test_mediator_conn_id,
            routing_keys=self.test_mediator_routing_keys,
            endpoint=self.test_mediator_endpoint,
        )
        doc = await self.manager.create_did_document(
            did_info, mediation_records=[mediation_record]
        )
        assert doc.service
        services = list(doc.service.values())
        assert len(services) == 1
        (service,) = services
        service_public_keys = service.routing_keys[0]
        assert service_public_keys.value == mediation_record.routing_keys[0]
        assert service.endpoint == mediation_record.endpoint

    async def test_create_did_document_multiple_mediators(self):
        did_info = DIDInfo(
            self.test_did,
            self.test_verkey,
            None,
            method=SOV,
            key_type=ED25519,
        )
        mediation_record1 = MediationRecord(
            role=MediationRecord.ROLE_CLIENT,
            state=MediationRecord.STATE_GRANTED,
            connection_id=self.test_mediator_conn_id,
            routing_keys=self.test_mediator_routing_keys,
            endpoint=self.test_mediator_endpoint,
        )
        mediation_record2 = MediationRecord(
            role=MediationRecord.ROLE_CLIENT,
            state=MediationRecord.STATE_GRANTED,
            connection_id="mediator-conn-id2",
            routing_keys=["05e8afd1-b4f0-46b7-a285-7a08c8a37caf"],
            endpoint="http://mediatorw.example.com",
        )
        doc = await self.manager.create_did_document(
            did_info, mediation_records=[mediation_record1, mediation_record2]
        )
        assert doc.service
        services = list(doc.service.values())
        assert len(services) == 1
        (service,) = services
        assert service.routing_keys[0].value == mediation_record1.routing_keys[0]
        assert service.routing_keys[1].value == mediation_record2.routing_keys[0]
        assert service.endpoint == mediation_record2.endpoint

    async def test_create_did_document_mediation_svc_endpoints_overwritten(self):
        did_info = DIDInfo(
            self.test_did,
            self.test_verkey,
            None,
            method=SOV,
            key_type=ED25519,
        )
        mediation_record = MediationRecord(
            role=MediationRecord.ROLE_CLIENT,
            state=MediationRecord.STATE_GRANTED,
            connection_id=self.test_mediator_conn_id,
            routing_keys=self.test_mediator_routing_keys,
            endpoint=self.test_mediator_endpoint,
        )
        doc = await self.manager.create_did_document(
            did_info,
            svc_endpoints=[self.test_endpoint],
            mediation_records=[mediation_record],
        )
        assert doc.service
        services = list(doc.service.values())
        assert len(services) == 1
        (service,) = services
        service_public_keys = service.routing_keys[0]
        assert service_public_keys.value == mediation_record.routing_keys[0]
        assert service.endpoint == mediation_record.endpoint

    async def test_did_key_storage(self):
        await self.manager.add_key_for_did(
            did=self.test_target_did, key=self.test_target_verkey
        )
        await self.manager.add_key_for_did(
            did=self.test_target_did, key=self.test_target_verkey
        )

        did = await self.manager.find_did_for_key(key=self.test_target_verkey)
        assert did == self.test_target_did
        await self.manager.remove_keys_for_did(self.test_target_did)

    async def test_store_did_document_with_routing_keys(self):
        """Regression test for ensuring agents with the same mediator can connect."""

        # Replicate old behavior where routing keys could be stored multiple times
        routing_key = "cK7fwfjpakMuv8QKVv2y6qouZddVw4TxZNQPUs2fFTd"
        async with self.profile.session() as session:
            for _ in range(3):
                record = StorageRecord(
                    self.manager.RECORD_TYPE_DID_KEY,
                    routing_key,
                    {"did": "bogus", "key": routing_key},
                )
                storage = session.inject(BaseStorage)
                await storage.add_record(record)

        # The DIDDoc class will turn the routing key into a publicKey entry.
        # This is NOT the correct behavior for normalizing DID Documents.
        # Unforunately, it's been doing it for a long time; to accomodate
        # stored records, we need to make sure we can handle duplicate records
        # where they shouldn't actually be.
        # These records were never used or else we would have seen errors raised
        # by find_did_for_key compaining of duplicate records.
        doc_with_routing_keys = DIDDoc.deserialize(
            {
                "@context": "https://w3id.org/did/v1",
                "publicKey": [
                    {
                        "id": "YQwDgq9vdAbB3fk1tkeXmg#1",
                        "controller": "YQwDgq9vdAbB3fk1tkeXmg",
                        "type": "Ed25519VerificationKey2018",
                        "publicKeyBase58": "J81x9zdJa8CGSbTYpoYQaNrV6yv13M1Lgz4tmkNPKwZn",
                    }
                ],
                "service": [
                    {
                        "id": "YQwDgq9vdAbB3fk1tkeXmg#IndyAgentService",
                        "serviceEndpoint": "https://aries-mediator-agent.vonx.io",
                        "type": "IndyAgent",
                        "priority": 0,
                        "recipientKeys": [
                            "J81x9zdJa8CGSbTYpoYQaNrV6yv13M1Lgz4tmkNPKwZn"
                        ],
                        "routingKeys": ["cK7fwfjpakMuv8QKVv2y6qouZddVw4TxZNQPUs2fFTd"],
                    }
                ],
                "authentication": [
                    {
                        "publicKey": "YQwDgq9vdAbB3fk1tkeXmg#1",
                        "type": "Ed25519SignatureAuthentication2018",
                    }
                ],
                "id": "YQwDgq9vdAbB3fk1tkeXmg",
            }
        )
        with self.assertLogs(level="WARNING") as context:
            await self.manager.store_did_document(doc_with_routing_keys)
        assert context.output and "Key already associated with DID" in context.output[0]

    async def test_fetch_connection_targets_no_my_did(self):
        mock_conn = async_mock.MagicMock()
        mock_conn.my_did = None
        assert await self.manager.fetch_connection_targets(mock_conn) == []

    async def test_fetch_connection_targets_conn_invitation_did_no_resolver(self):
        async with self.profile.session() as session:
            self.context.injector.bind_instance(DIDResolver, DIDResolver([]))
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            conn_invite = ConnectionInvitation(
                did=self.test_target_did,
                endpoint=self.test_endpoint,
                recipient_keys=[self.test_target_verkey],
                routing_keys=[self.test_verkey],
                label="label",
            )
            mock_conn = async_mock.MagicMock(
                my_did=self.test_did,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(return_value=conn_invite),
            )

            with self.assertRaises(BaseConnectionManagerError):
                await self.manager.fetch_connection_targets(mock_conn)

    async def test_fetch_connection_targets_conn_invitation_did_resolver(self):
        async with self.profile.session() as session:
            builder = DIDDocumentBuilder("did:sov:" + self.test_target_did)
            vmethod = builder.verification_method.add(
                Ed25519VerificationKey2018, public_key_base58=self.test_target_verkey
            )
            builder.service.add_didcomm(
                ident="did-communication",
                service_endpoint=self.test_endpoint,
                recipient_keys=[vmethod],
            )
            did_doc = builder.build()
            self.resolver.get_endpoint_for_did = async_mock.CoroutineMock(
                return_value=self.test_endpoint
            )
            self.resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
            self.resolver.dereference = async_mock.CoroutineMock(
                return_value=did_doc.verification_method[0]
            )
            self.context.injector.bind_instance(DIDResolver, self.resolver)

            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            conn_invite = ConnectionInvitation(
                did=self.test_target_did,
                endpoint=self.test_endpoint,
                recipient_keys=[self.test_target_verkey],
                routing_keys=[self.test_verkey],
                label="label",
            )
            mock_conn = async_mock.MagicMock(
                my_did=self.test_did,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(return_value=conn_invite),
            )

            targets = await self.manager.fetch_connection_targets(mock_conn)
            assert len(targets) == 1
            target = targets[0]
            assert target.did == mock_conn.their_did
            assert target.endpoint == conn_invite.endpoint
            assert target.label == conn_invite.label
            assert target.recipient_keys == conn_invite.recipient_keys
            assert target.routing_keys == []
            assert target.sender_key == local_did.verkey

    async def test_fetch_connection_targets_conn_invitation_btcr_resolver(self):
        async with self.profile.session() as session:
            builder = DIDDocumentBuilder("did:btcr:x705-jznz-q3nl-srs")
            vmethod = builder.verification_method.add(
                Ed25519VerificationKey2018, public_key_base58=self.test_target_verkey
            )
            builder.service.add_didcomm(
                type_="IndyAgent",
                recipient_keys=[vmethod],
                routing_keys=[vmethod],
                service_endpoint=self.test_endpoint,
                priority=1,
            )

            builder.service.add_didcomm(
                recipient_keys=[vmethod],
                routing_keys=[vmethod],
                service_endpoint=self.test_endpoint,
                priority=0,
            )
            builder.service.add_didcomm(
                recipient_keys=[vmethod],
                routing_keys=[vmethod],
                service_endpoint="{}/priority2".format(self.test_endpoint),
                priority=2,
            )
            did_doc = builder.build()

            self.resolver.get_endpoint_for_did = async_mock.CoroutineMock(
                return_value=self.test_endpoint
            )
            self.resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
            self.resolver.dereference = async_mock.CoroutineMock(
                return_value=did_doc.verification_method[0]
            )
            self.context.injector.bind_instance(DIDResolver, self.resolver)
            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=did_doc.id,
                metadata=None,
            )

            conn_invite = ConnectionInvitation(
                did=did_doc.id,
                endpoint=self.test_endpoint,
                recipient_keys=[vmethod.material],
                routing_keys=[self.test_verkey],
                label="label",
            )
            mock_conn = async_mock.MagicMock(
                my_did=did_doc.id,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(return_value=conn_invite),
            )

            targets = await self.manager.fetch_connection_targets(mock_conn)
            assert len(targets) == 1
            target = targets[0]
            assert target.did == mock_conn.their_did
            assert target.endpoint == self.test_endpoint
            assert target.label == conn_invite.label
            assert target.recipient_keys == conn_invite.recipient_keys
            assert target.routing_keys == [vmethod.material]
            assert target.sender_key == local_did.verkey

    async def test_fetch_connection_targets_conn_invitation_btcr_without_services(self):
        async with self.profile.session() as session:
            did_doc_json = {
                "@context": ["https://www.w3.org/ns/did/v1"],
                "id": "did:btcr:x705-jznz-q3nl-srs",
                "verificationMethod": [
                    {
                        "type": "EcdsaSecp256k1VerificationKey2019",
                        "id": "did:btcr:x705-jznz-q3nl-srs#key-0",
                        "publicKeyBase58": "02e0e01a8c302976e1556e95c54146e8464adac8626a5d29474718a7281133ff49",
                    },
                    {
                        "type": "EcdsaSecp256k1VerificationKey2019",
                        "id": "did:btcr:x705-jznz-q3nl-srs#key-1",
                        "publicKeyBase58": "02e0e01a8c302976e1556e95c54146e8464adac8626a5d29474718a7281133ff49",
                    },
                    {
                        "type": "EcdsaSecp256k1VerificationKey2019",
                        "id": "did:btcr:x705-jznz-q3nl-srs#satoshi",
                        "publicKeyBase58": "02e0e01a8c302976e1556e95c54146e8464adac8626a5d29474718a7281133ff49",
                    },
                ],
            }
            did_doc = DIDDocument.deserialize(did_doc_json)
            self.resolver.get_endpoint_for_did = async_mock.CoroutineMock(
                return_value=self.test_endpoint
            )
            self.resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
            self.context.injector.bind_instance(DIDResolver, self.resolver)

            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=did_doc.id,
                metadata=None,
            )

            conn_invite = ConnectionInvitation(
                did=did_doc.id,
                endpoint=self.test_endpoint,
                recipient_keys=["{}#1".format(did_doc.id)],
                routing_keys=[self.test_verkey],
                label="label",
            )
            mock_conn = async_mock.MagicMock(
                my_did=did_doc.id,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(return_value=conn_invite),
            )
            with self.assertRaises(BaseConnectionManagerError):
                await self.manager.fetch_connection_targets(mock_conn)

    async def test_fetch_connection_targets_conn_invitation_no_didcomm_services(self):
        async with self.profile.session() as session:
            builder = DIDDocumentBuilder("did:btcr:x705-jznz-q3nl-srs")
            builder.verification_method.add(
                Ed25519VerificationKey2018, public_key_base58=self.test_target_verkey
            )
            builder.service.add(type_="LinkedData", service_endpoint=self.test_endpoint)
            did_doc = builder.build()
            self.resolver.get_endpoint_for_did = async_mock.CoroutineMock(
                return_value=self.test_endpoint
            )
            self.resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
            self.context.injector.bind_instance(DIDResolver, self.resolver)
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=did_doc.id,
                metadata=None,
            )

            conn_invite = ConnectionInvitation(
                did=did_doc.id,
                endpoint=self.test_endpoint,
                recipient_keys=["{}#1".format(did_doc.id)],
                routing_keys=[self.test_verkey],
                label="label",
            )
            mock_conn = async_mock.MagicMock(
                my_did=did_doc.id,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(return_value=conn_invite),
            )
            with self.assertRaises(BaseConnectionManagerError):
                await self.manager.fetch_connection_targets(mock_conn)

    async def test_fetch_connection_targets_conn_invitation_supports_Ed25519VerificationKey2018_key_type_no_multicodec(
        self,
    ):
        async with self.profile.session() as session:
            builder = DIDDocumentBuilder("did:btcr:x705-jznz-q3nl-srs")
            vmethod = builder.verification_method.add(
                Ed25519VerificationKey2020,
                public_key_multibase=multibase.encode(
                    b58_to_bytes(self.test_target_verkey), "base58btc"
                ),
            )
            builder.service.add_didcomm(
                type_="IndyAgent",
                service_endpoint=self.test_endpoint,
                recipient_keys=[vmethod],
            )
            did_doc = builder.build()
            self.resolver.get_endpoint_for_did = async_mock.CoroutineMock(
                return_value=self.test_endpoint
            )
            self.resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
            self.resolver.dereference = async_mock.CoroutineMock(
                return_value=did_doc.verification_method[0]
            )
            self.context.injector.bind_instance(DIDResolver, self.resolver)
            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=did_doc.id,
                metadata=None,
            )

            conn_invite = ConnectionInvitation(
                did=did_doc.id,
                endpoint=self.test_endpoint,
                recipient_keys=[vmethod.public_key_jwk],
                routing_keys=[self.test_verkey],
                label="label",
            )
            mock_conn = async_mock.MagicMock(
                my_did=did_doc.id,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(return_value=conn_invite),
            )

            targets = await self.manager.fetch_connection_targets(mock_conn)
            assert len(targets) == 1
            target = targets[0]
            assert target.did == mock_conn.their_did
            assert target.endpoint == self.test_endpoint
            assert target.label == conn_invite.label
            assert target.recipient_keys == [self.test_target_verkey]
            assert target.routing_keys == []
            assert target.sender_key == local_did.verkey

    async def test_fetch_connection_targets_conn_invitation_supports_Ed25519VerificationKey2018_key_type_with_multicodec(
        self,
    ):
        async with self.profile.session() as session:
            builder = DIDDocumentBuilder("did:btcr:x705-jznz-q3nl-srs")
            vmethod = builder.verification_method.add(
                Ed25519VerificationKey2020,
                public_key_multibase=multibase.encode(
                    multicodec.wrap(
                        "ed25519-pub", b58_to_bytes(self.test_target_verkey)
                    ),
                    "base58btc",
                ),
            )
            builder.service.add_didcomm(
                type_="IndyAgent",
                service_endpoint=self.test_endpoint,
                recipient_keys=[vmethod],
            )
            did_doc = builder.build()
            self.resolver.get_endpoint_for_did = async_mock.CoroutineMock(
                return_value=self.test_endpoint
            )
            self.resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
            self.resolver.dereference = async_mock.CoroutineMock(
                return_value=did_doc.verification_method[0]
            )
            self.context.injector.bind_instance(DIDResolver, self.resolver)
            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=did_doc.id,
                metadata=None,
            )

            conn_invite = ConnectionInvitation(
                did=did_doc.id,
                endpoint=self.test_endpoint,
                recipient_keys=[vmethod.public_key_jwk],
                routing_keys=[self.test_verkey],
                label="label",
            )
            mock_conn = async_mock.MagicMock(
                my_did=did_doc.id,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(return_value=conn_invite),
            )

            targets = await self.manager.fetch_connection_targets(mock_conn)
            assert len(targets) == 1
            target = targets[0]
            assert target.did == mock_conn.their_did
            assert target.endpoint == self.test_endpoint
            assert target.label == conn_invite.label
            assert target.recipient_keys == [self.test_target_verkey]
            assert target.routing_keys == []
            assert target.sender_key == local_did.verkey

    async def test_fetch_connection_targets_conn_invitation_supported_JsonWebKey2020_key_type(
        self,
    ):
        async with self.profile.session() as session:
            builder = DIDDocumentBuilder("did:btcr:x705-jznz-q3nl-srs")
            vmethod = builder.verification_method.add(
                JsonWebKey2020,
                ident="1",
                public_key_jwk={
                    "kty": "OKP",
                    "crv": "Ed25519",
                    "x": bytes_to_b64(b58_to_bytes(self.test_target_verkey), True),
                },
            )
            builder.service.add_didcomm(
                type_="IndyAgent",
                service_endpoint=self.test_endpoint,
                recipient_keys=[vmethod],
            )
            did_doc = builder.build()
            self.resolver.get_endpoint_for_did = async_mock.CoroutineMock(
                return_value=self.test_endpoint
            )
            self.resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
            self.resolver.dereference = async_mock.CoroutineMock(
                return_value=did_doc.verification_method[0]
            )
            self.context.injector.bind_instance(DIDResolver, self.resolver)
            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=did_doc.id,
                metadata=None,
            )

            conn_invite = ConnectionInvitation(
                did=did_doc.id,
                endpoint=self.test_endpoint,
                recipient_keys=[vmethod.public_key_jwk],
                routing_keys=[self.test_verkey],
                label="label",
            )
            mock_conn = async_mock.MagicMock(
                my_did=did_doc.id,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(return_value=conn_invite),
            )

            targets = await self.manager.fetch_connection_targets(mock_conn)
            assert len(targets) == 1
            target = targets[0]
            assert target.did == mock_conn.their_did
            assert target.endpoint == self.test_endpoint
            assert target.label == conn_invite.label
            assert target.recipient_keys == [self.test_target_verkey]
            assert target.routing_keys == []
            assert target.sender_key == local_did.verkey

    async def test_fetch_connection_targets_conn_invitation_unsupported_key_type(self):
        async with self.profile.session() as session:
            builder = DIDDocumentBuilder("did:btcr:x705-jznz-q3nl-srs")
            vmethod = builder.verification_method.add(
                JsonWebKey2020,
                ident="1",
                public_key_jwk={
                    "kty": "EC",
                    "crv": "P-256",
                    "x": "2syLh57B-dGpa0F8p1JrO6JU7UUSF6j7qL-vfk1eOoY",
                    "y": "BgsGtI7UPsObMRjdElxLOrgAO9JggNMjOcfzEPox18w",
                },
            )
            builder.service.add_didcomm(
                type_="IndyAgent",
                service_endpoint=self.test_endpoint,
                recipient_keys=[vmethod],
            )
            did_doc = builder.build()
            self.resolver.get_endpoint_for_did = async_mock.CoroutineMock(
                return_value=self.test_endpoint
            )
            self.resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
            self.resolver.dereference = async_mock.CoroutineMock(
                return_value=did_doc.verification_method[0]
            )
            self.context.injector.bind_instance(DIDResolver, self.resolver)
            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=did_doc.id,
                metadata=None,
            )

            conn_invite = ConnectionInvitation(
                did=did_doc.id,
                endpoint=self.test_endpoint,
                recipient_keys=["{}#1".format(did_doc.id)],
                routing_keys=[self.test_verkey],
                label="label",
            )
            mock_conn = async_mock.MagicMock(
                my_did=did_doc.id,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(return_value=conn_invite),
            )
            with self.assertRaises(BaseConnectionManagerError):
                await self.manager.fetch_connection_targets(mock_conn)

    async def test_fetch_connection_targets_oob_invitation_svc_did_no_resolver(self):
        async with self.profile.session() as session:
            self.context.injector.bind_instance(DIDResolver, DIDResolver([]))
            await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            mock_oob_invite = async_mock.MagicMock(services=[self.test_did])

            mock_conn = async_mock.MagicMock(
                my_did=self.test_did,
                retrieve_invitation=async_mock.CoroutineMock(
                    return_value=mock_oob_invite
                ),
                state=ConnRecord.State.INVITATION.rfc23,
                their_role=ConnRecord.Role.RESPONDER.rfc23,
            )

            with self.assertRaises(BaseConnectionManagerError):
                await self.manager.fetch_connection_targets(mock_conn)

    async def test_fetch_connection_targets_oob_invitation_svc_did_resolver(self):
        async with self.profile.session() as session:
            builder = DIDDocumentBuilder("did:sov:" + self.test_target_did)
            vmethod = builder.verification_method.add(
                Ed25519VerificationKey2018,
                ident="1",
                public_key_base58=self.test_target_verkey,
            )
            builder.service.add_didcomm(
                ident="did-communication",
                service_endpoint=self.test_endpoint,
                recipient_keys=[vmethod],
            )
            did_doc = builder.build()

            self.resolver.resolve = async_mock.CoroutineMock(return_value=did_doc)
            self.resolver.dereference = async_mock.CoroutineMock(
                return_value=did_doc.verification_method[0]
            )
            self.context.injector.bind_instance(DIDResolver, self.resolver)

            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            mock_oob_invite = async_mock.MagicMock(
                label="a label",
                their_did=self.test_target_did,
                services=["dummy"],
            )
            mock_conn = async_mock.MagicMock(
                my_did=self.test_did,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(
                    return_value=mock_oob_invite
                ),
            )

            targets = await self.manager.fetch_connection_targets(mock_conn)
            assert len(targets) == 1
            target = targets[0]
            assert target.did == mock_conn.their_did
            assert target.endpoint == self.test_endpoint
            assert target.label == mock_oob_invite.label
            assert target.recipient_keys == [vmethod.material]
            assert target.routing_keys == []
            assert target.sender_key == local_did.verkey

    async def test_fetch_connection_targets_oob_invitation_svc_block_resolver(self):
        async with self.profile.session() as session:
            self.resolver.get_endpoint_for_did = async_mock.CoroutineMock(
                return_value=self.test_endpoint
            )
            self.resolver.get_key_for_did = async_mock.CoroutineMock(
                return_value=self.test_target_verkey
            )
            self.context.injector.bind_instance(DIDResolver, self.resolver)

            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            mock_oob_invite = async_mock.MagicMock(
                label="a label",
                their_did=self.test_target_did,
                services=[
                    async_mock.MagicMock(
                        service_endpoint=self.test_endpoint,
                        recipient_keys=[
                            DIDKey.from_public_key_b58(
                                self.test_target_verkey, ED25519
                            ).did
                        ],
                        routing_keys=[],
                    )
                ],
            )
            mock_conn = async_mock.MagicMock(
                my_did=self.test_did,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(
                    return_value=mock_oob_invite
                ),
            )

            targets = await self.manager.fetch_connection_targets(mock_conn)
            assert len(targets) == 1
            target = targets[0]
            assert target.did == mock_conn.their_did
            assert target.endpoint == self.test_endpoint
            assert target.label == mock_oob_invite.label
            assert target.recipient_keys == [self.test_target_verkey]
            assert target.routing_keys == []
            assert target.sender_key == local_did.verkey

    async def test_fetch_connection_targets_conn_initiator_completed_no_their_did(self):
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
                their_did=None,
                state=ConnRecord.State.COMPLETED.rfc23,
            )
            assert await self.manager.fetch_connection_targets(mock_conn) == []

    async def test_fetch_connection_targets_conn_completed_their_did(self):
        async with self.profile.session() as session:
            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            did_doc = self.make_did_doc(did=self.test_did, verkey=self.test_verkey)
            await self.manager.store_did_document(did_doc)

            mock_conn = async_mock.MagicMock(
                my_did=self.test_did,
                their_did=self.test_did,
                their_label="label",
                their_role=ConnRecord.Role.REQUESTER.rfc160,
                state=ConnRecord.State.COMPLETED.rfc23,
            )

            targets = await self.manager.fetch_connection_targets(mock_conn)
            assert len(targets) == 1
            target = targets[0]
            # did:sov: dropped for this check
            assert target.did[8:] == mock_conn.their_did
            assert target.endpoint == self.test_endpoint
            assert target.label == mock_conn.their_label
            assert target.recipient_keys == [self.test_verkey]
            assert target.routing_keys == []
            assert target.sender_key == local_did.verkey

    async def test_fetch_connection_targets_conn_no_invi_with_their_did(self):
        async with self.profile.session() as session:
            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            self.manager.resolve_invitation = async_mock.CoroutineMock()
            self.manager.resolve_invitation.return_value = (
                self.test_endpoint,
                [self.test_verkey],
                [],
            )

            did_doc = self.make_did_doc(did=self.test_did, verkey=self.test_verkey)
            await self.manager.store_did_document(did_doc)

            mock_conn = async_mock.MagicMock(
                my_did=self.test_did,
                their_did=self.test_did,
                their_label="label",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.REQUEST.rfc23,
                invitation_key=None,
                invitation_msg_id=None,
            )

            targets = await self.manager.fetch_connection_targets(mock_conn)
            assert len(targets) == 1
            target = targets[0]
            assert target.did == mock_conn.their_did
            assert target.endpoint == self.test_endpoint
            assert target.label is None
            assert target.recipient_keys == [self.test_verkey]
            assert target.routing_keys == []
            assert target.sender_key == local_did.verkey

    async def test_verification_methods_for_service(self):
        did = "did:sov:" + self.test_did
        doc_builder = DIDDocumentBuilder(did)
        vm = doc_builder.verification_method.add(
            Ed25519VerificationKey2018,
            public_key_base58=self.test_verkey,
        )
        route_key = DIDKey.from_public_key_b58(self.test_verkey, ED25519)
        service = doc_builder.service.add(
            type_="did-communication",
            service_endpoint=self.test_endpoint,
            recipient_keys=[vm.id],
            routing_keys=[route_key.key_id],
        )
        doc = doc_builder.build()
        self.manager.resolve_didcomm_services = async_mock.CoroutineMock(
            return_value=(doc, doc.service)
        )
        recip, routing = await self.manager.verification_methods_for_service(
            doc, service
        )
        assert recip == [vm]
        assert routing

    async def test_resolve_connection_targets_empty(self):
        """Test resolve connection targets."""
        did = "did:sov:" + self.test_did
        self.manager.resolve_didcomm_services = async_mock.CoroutineMock(
            return_value=(DIDDocument(id=DID(did)), [])
        )
        targets = await self.manager.resolve_connection_targets(did)
        assert targets == []

    async def test_resolve_connection_targets(self):
        """Test resolve connection targets."""
        did = "did:sov:" + self.test_did
        doc_builder = DIDDocumentBuilder(did)
        vm = doc_builder.verification_method.add(
            Ed25519VerificationKey2018,
            public_key_base58=self.test_verkey,
        )
        route_key = DIDKey.from_public_key_b58(self.test_verkey, ED25519)
        doc_builder.service.add(
            type_="did-communication",
            service_endpoint=self.test_endpoint,
            recipient_keys=[vm.id],
            routing_keys=[route_key.key_id],
        )
        doc = doc_builder.build()
        self.manager.resolve_didcomm_services = async_mock.CoroutineMock(
            return_value=(doc, doc.service)
        )
        targets = await self.manager.resolve_connection_targets(did)
        assert targets
        assert targets[0].routing_keys[0] == self.test_verkey

    async def test_resolve_connection_targets_x_bad_reference(self):
        """Test resolve connection targets."""
        did = "did:sov:" + self.test_did
        doc_builder = DIDDocumentBuilder(did)
        vm = doc_builder.verification_method.add(
            Ed25519VerificationKey2018,
            public_key_base58=self.test_verkey,
        )
        doc_builder.service.add(
            type_="did-communication",
            service_endpoint=self.test_endpoint,
            recipient_keys=[vm.id],
            routing_keys=["did:example:123#some-random-id"],
        )
        doc = doc_builder.build()
        self.manager.resolve_didcomm_services = async_mock.CoroutineMock(
            return_value=(doc, doc.service)
        )
        with self.assertLogs() as cm:
            await self.manager.resolve_connection_targets(did)
        assert cm.output and "Failed to resolve service" in cm.output[0]

    async def test_resolve_connection_targets_x_bad_key_material(self):
        did = "did:sov:" + self.test_did
        doc_builder = DIDDocumentBuilder(did)
        vm = doc_builder.verification_method.add(
            Ed25519VerificationKey2020,
            public_key_multibase=multibase.encode(
                multicodec.wrap("secp256k1-pub", b58_to_bytes(self.test_verkey)),
                "base58btc",
            ),
        )
        route_key = DIDKey.from_public_key_b58(self.test_verkey, ED25519)
        doc_builder.service.add(
            type_="did-communication",
            service_endpoint=self.test_endpoint,
            recipient_keys=[vm.id],
            routing_keys=[route_key.key_id],
        )
        doc = doc_builder.build()
        self.manager.resolve_didcomm_services = async_mock.CoroutineMock(
            return_value=(doc, doc.service)
        )
        with self.assertRaises(BaseConnectionManagerError) as cm:
            await self.manager.resolve_connection_targets(did)
        assert "not supported" in str(cm.exception)

    async def test_resolve_connection_targets_x_unsupported_key(self):
        did = "did:sov:" + self.test_did
        doc_builder = DIDDocumentBuilder(did)
        vm = doc_builder.verification_method.add(
            EcdsaSecp256k1VerificationKey2019,
            public_key_hex="deadbeef",
        )
        route_key = DIDKey.from_public_key_b58(self.test_verkey, ED25519)
        doc_builder.service.add(
            type_="did-communication",
            service_endpoint=self.test_endpoint,
            recipient_keys=[vm.id],
            routing_keys=[route_key.key_id],
        )
        doc = doc_builder.build()
        self.manager.resolve_didcomm_services = async_mock.CoroutineMock(
            return_value=(doc, doc.service)
        )
        with self.assertRaises(BaseConnectionManagerError) as cm:
            await self.manager.resolve_connection_targets(did)
        assert "not supported" in str(cm.exception)

    async def test_record_keys_for_public_did_empty(self):
        did = "did:sov:" + self.test_did
        service_builder = ServiceBuilder(DID(did))
        service_builder.add_didcomm(
            self.test_endpoint, recipient_keys=[], routing_keys=[]
        )
        self.manager.resolve_didcomm_services = async_mock.CoroutineMock(
            return_value=(DIDDocument(id=DID(did)), service_builder.services)
        )
        await self.manager.record_keys_for_public_did(did)

    async def test_record_keys_for_public_did(self):
        did = "did:sov:" + self.test_did
        doc_builder = DIDDocumentBuilder(did)
        vm = doc_builder.verification_method.add(
            Ed25519VerificationKey2018,
            public_key_base58=self.test_verkey,
        )
        doc_builder.service.add_didcomm(
            self.test_endpoint, recipient_keys=[vm], routing_keys=[]
        )
        doc = doc_builder.build()
        self.manager.resolve_didcomm_services = async_mock.CoroutineMock(
            return_value=(doc, doc.service)
        )
        await self.manager.record_keys_for_public_did(did)

    async def test_diddoc_connection_targets_diddoc_underspecified(self):
        with self.assertRaises(BaseConnectionManagerError):
            self.manager.diddoc_connection_targets(None, self.test_verkey)

        x_did_doc = DIDDoc(did=None)
        with self.assertRaises(BaseConnectionManagerError):
            self.manager.diddoc_connection_targets(x_did_doc, self.test_verkey)

        x_did_doc = self.make_did_doc(
            did=self.test_target_did, verkey=self.test_target_verkey
        )
        x_did_doc._service = {}
        with self.assertRaises(BaseConnectionManagerError):
            self.manager.diddoc_connection_targets(x_did_doc, self.test_verkey)

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
            BaseConnectionManager,
            "resolve_inbound_connection",
            async_mock.CoroutineMock(),
        ) as mock_conn_mgr_resolve_conn:
            mock_conn_mgr_resolve_conn.return_value = mock_conn

            conn_rec = await self.manager.find_inbound_connection(receipt)
            assert conn_rec

        # Second pass: in cache
        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
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
            BaseConnectionManager,
            "resolve_inbound_connection",
            async_mock.CoroutineMock(),
        ) as mock_conn_mgr_resolve_conn:
            self.context.injector.clear_binding(BaseCache)
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
            InMemoryWallet, "get_local_did_for_verkey", async_mock.CoroutineMock()
        ) as mock_wallet_get_local_did_for_verkey, async_mock.patch.object(
            self.manager, "find_connection", async_mock.CoroutineMock()
        ) as mock_mgr_find_conn:
            mock_wallet_get_local_did_for_verkey.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                {"posted": True},
                method=SOV,
                key_type=ED25519,
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
            InMemoryWallet, "get_local_did_for_verkey", async_mock.CoroutineMock()
        ) as mock_wallet_get_local_did_for_verkey, async_mock.patch.object(
            self.manager, "find_connection", async_mock.CoroutineMock()
        ) as mock_mgr_find_conn:
            mock_wallet_get_local_did_for_verkey.side_effect = InjectionError()
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
            InMemoryWallet, "get_local_did_for_verkey", async_mock.CoroutineMock()
        ) as mock_wallet_get_local_did_for_verkey, async_mock.patch.object(
            self.manager, "find_connection", async_mock.CoroutineMock()
        ) as mock_mgr_find_conn:
            mock_wallet_get_local_did_for_verkey.side_effect = WalletNotFoundError()
            mock_mgr_find_conn.return_value = mock_conn

            assert await self.manager.resolve_inbound_connection(receipt)

    async def test_get_connection_targets_conn_invitation_no_did(self):
        async with self.profile.session() as session:
            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            did_doc = self.make_did_doc(
                did=self.test_target_did, verkey=self.test_target_verkey
            )
            await self.manager.store_did_document(did_doc)

            # First pass: not yet in cache
            conn_invite = ConnectionInvitation(
                did=None,
                endpoint=self.test_endpoint,
                recipient_keys=[self.test_target_verkey],
                routing_keys=[self.test_verkey],
                label="label",
            )
            mock_conn = async_mock.MagicMock(
                my_did=self.test_did,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(return_value=conn_invite),
            )

            targets = await self.manager.get_connection_targets(
                connection_id=None,
                connection=mock_conn,
            )
            assert len(targets) == 1
            target = targets[0]
            assert target.did == mock_conn.their_did
            assert target.endpoint == conn_invite.endpoint
            assert target.label == conn_invite.label
            assert target.recipient_keys == conn_invite.recipient_keys
            assert target.routing_keys == conn_invite.routing_keys
            assert target.sender_key == local_did.verkey

            # Next pass: exercise cache
            targets = await self.manager.get_connection_targets(
                connection_id=None,
                connection=mock_conn,
            )
            assert len(targets) == 1
            target = targets[0]
            assert target.did == mock_conn.their_did
            assert target.endpoint == conn_invite.endpoint
            assert target.label == conn_invite.label
            assert target.recipient_keys == conn_invite.recipient_keys
            assert target.routing_keys == conn_invite.routing_keys
            assert target.sender_key == local_did.verkey

    async def test_get_connection_targets_retrieve_connection(self):
        async with self.profile.session() as session:
            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            did_doc = self.make_did_doc(
                did=self.test_target_did, verkey=self.test_target_verkey
            )
            await self.manager.store_did_document(did_doc)

            # Connection target not in cache
            conn_invite = ConnectionInvitation(
                did=None,
                endpoint=self.test_endpoint,
                recipient_keys=[self.test_target_verkey],
                routing_keys=[self.test_verkey],
                label="label",
            )
            mock_conn = async_mock.MagicMock(
                my_did=self.test_did,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(return_value=conn_invite),
            )

            with async_mock.patch.object(
                ConnectionTarget, "serialize", autospec=True
            ) as mock_conn_target_ser, async_mock.patch.object(
                ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
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
                assert target.endpoint == conn_invite.endpoint
                assert target.label == conn_invite.label
                assert target.recipient_keys == conn_invite.recipient_keys
                assert target.routing_keys == conn_invite.routing_keys
                assert target.sender_key == local_did.verkey

    async def test_get_connection_targets_from_cache(self):
        async with self.profile.session() as session:
            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            did_doc = self.make_did_doc(
                did=self.test_target_did, verkey=self.test_target_verkey
            )
            await self.manager.store_did_document(did_doc)

            mock_conn = async_mock.MagicMock(
                my_did=self.test_did,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.COMPLETED.rfc160,
            )

            with async_mock.patch.object(
                ConnectionTarget, "serialize", autospec=True
            ) as mock_conn_target_ser, async_mock.patch.object(
                ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
                self.manager, "fetch_connection_targets", async_mock.CoroutineMock()
            ) as mock_fetch_connection_targets:
                mock_fetch_connection_targets.return_value = [ConnectionTarget()]
                mock_conn_rec_retrieve_by_id.return_value = mock_conn
                mock_conn_target_ser.return_value = {"serialized": "value"}
                targets = await self.manager.get_connection_targets(
                    connection_id="dummy",
                    connection=None,
                )

                cached_targets = await self.manager.get_connection_targets(
                    connection_id="dummy",
                    connection=None,
                )
                assert mock_fetch_connection_targets.call_count == 1

    async def test_get_connection_targets_no_cache(self):
        async with self.profile.session() as session:
            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            did_doc = self.make_did_doc(
                did=self.test_target_did, verkey=self.test_target_verkey
            )
            await self.manager.store_did_document(did_doc)

            mock_conn = async_mock.MagicMock(
                my_did=self.test_did,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.COMPLETED.rfc160,
            )

            with async_mock.patch.object(
                ConnectionTarget, "serialize", autospec=True
            ) as mock_conn_target_ser, async_mock.patch.object(
                ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
                self.manager, "fetch_connection_targets", async_mock.CoroutineMock()
            ) as mock_fetch_connection_targets:
                mock_fetch_connection_targets.return_value = [ConnectionTarget()]
                mock_conn_rec_retrieve_by_id.return_value = mock_conn
                mock_conn_target_ser.return_value = {"serialized": "value"}
                self.profile.context.injector.clear_binding(BaseCache)
                targets = await self.manager.get_connection_targets(
                    connection_id="dummy",
                    connection=None,
                )
                assert targets
                targets = await self.manager.get_connection_targets(
                    connection_id=None,
                    connection=mock_conn,
                )
                assert targets

    async def test_get_connection_targets_no_conn_or_id(self):
        with self.assertRaises(ValueError):
            await self.manager.get_connection_targets()

    async def test_get_conn_targets_conn_invitation_no_cache(self):
        async with self.profile.session() as session:
            self.context.injector.clear_binding(BaseCache)
            local_did = await session.wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=self.test_seed,
                did=self.test_did,
                metadata=None,
            )

            did_doc = self.make_did_doc(
                did=self.test_target_did, verkey=self.test_target_verkey
            )
            await self.manager.store_did_document(did_doc)

            conn_invite = ConnectionInvitation(
                did=None,
                endpoint=self.test_endpoint,
                recipient_keys=[self.test_target_verkey],
                routing_keys=[self.test_verkey],
                label="label",
            )
            mock_conn = async_mock.MagicMock(
                my_did=self.test_did,
                their_did=self.test_target_did,
                connection_id="dummy",
                their_role=ConnRecord.Role.RESPONDER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                retrieve_invitation=async_mock.CoroutineMock(return_value=conn_invite),
            )

            targets = await self.manager.get_connection_targets(
                connection_id=None,
                connection=mock_conn,
            )
            assert len(targets) == 1
            target = targets[0]
            assert target.did == mock_conn.their_did
            assert target.endpoint == conn_invite.endpoint
            assert target.label == conn_invite.label
            assert target.recipient_keys == conn_invite.recipient_keys
            assert target.routing_keys == conn_invite.routing_keys
            assert target.sender_key == local_did.verkey

    async def test_create_static_connection(self):
        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save:
            _my, _their, conn_rec = await self.manager.create_static_connection(
                my_did=self.test_did,
                their_did=self.test_target_did,
                their_verkey=self.test_target_verkey,
                their_endpoint=self.test_endpoint,
            )

            assert ConnRecord.State.get(conn_rec.state) is ConnRecord.State.COMPLETED

    async def test_create_static_connection_multitenant(self):
        self.context.update_settings(
            {"wallet.id": "test_wallet", "multitenant.enabled": True}
        )

        self.multitenant_mgr.get_default_mediator.return_value = None

        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ), async_mock.patch.object(
            InMemoryWallet, "create_local_did", autospec=True
        ) as mock_wallet_create_local_did:
            mock_wallet_create_local_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )

            await self.manager.create_static_connection(
                my_did=self.test_did,
                their_did=self.test_target_did,
                their_verkey=self.test_target_verkey,
                their_endpoint=self.test_endpoint,
            )

            self.route_manager.route_static.assert_called_once()

    async def test_create_static_connection_multitenant_auto_disclose_features(self):
        self.context.update_settings(
            {
                "auto_disclose_features": True,
                "multitenant.enabled": True,
                "wallet.id": "test_wallet",
            }
        )
        self.multitenant_mgr.get_default_mediator.return_value = None
        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ), async_mock.patch.object(
            InMemoryWallet, "create_local_did", autospec=True
        ) as mock_wallet_create_local_did, async_mock.patch.object(
            V20DiscoveryMgr, "proactive_disclose_features", async_mock.CoroutineMock()
        ) as mock_proactive_disclose_features:
            mock_wallet_create_local_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )
            await self.manager.create_static_connection(
                my_did=self.test_did,
                their_did=self.test_target_did,
                their_verkey=self.test_target_verkey,
                their_endpoint=self.test_endpoint,
            )
            self.route_manager.route_static.assert_called_once()
            mock_proactive_disclose_features.assert_called_once()

    async def test_create_static_connection_multitenant_mediator(self):
        self.context.update_settings(
            {"wallet.id": "test_wallet", "multitenant.enabled": True}
        )

        default_mediator = async_mock.MagicMock()

        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ), async_mock.patch.object(
            InMemoryWallet, "create_local_did", autospec=True
        ) as mock_wallet_create_local_did, async_mock.patch.object(
            BaseConnectionManager, "create_did_document"
        ) as create_did_document, async_mock.patch.object(
            BaseConnectionManager, "store_did_document"
        ) as store_did_document:
            mock_wallet_create_local_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )

            # With default mediator
            self.multitenant_mgr.get_default_mediator.return_value = default_mediator
            await self.manager.create_static_connection(
                my_did=self.test_did,
                their_did=self.test_target_did,
                their_verkey=self.test_target_verkey,
                their_endpoint=self.test_endpoint,
            )

            # Without default mediator
            self.multitenant_mgr.get_default_mediator.return_value = None
            await self.manager.create_static_connection(
                my_did=self.test_did,
                their_did=self.test_target_did,
                their_verkey=self.test_target_verkey,
                their_endpoint=self.test_endpoint,
            )

            assert self.route_manager.route_static.call_count == 2

            their_info = DIDInfo(
                self.test_target_did,
                self.test_target_verkey,
                {},
                method=SOV,
                key_type=ED25519,
            )
            create_did_document.assert_has_calls(
                [
                    call(
                        their_info,
                        None,
                        [self.test_endpoint],
                        mediation_records=[default_mediator],
                    ),
                    call(their_info, None, [self.test_endpoint], mediation_records=[]),
                ]
            )

    async def test_create_static_connection_no_their(self):
        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save:
            with self.assertRaises(BaseConnectionManagerError):
                await self.manager.create_static_connection(
                    my_did=self.test_did,
                    their_did=None,
                    their_verkey=self.test_target_verkey,
                    their_endpoint=self.test_endpoint,
                )

    async def test_create_static_connection_their_seed_only(self):
        with async_mock.patch.object(
            ConnRecord, "save", autospec=True
        ) as mock_conn_rec_save:
            _my, _their, conn_rec = await self.manager.create_static_connection(
                my_did=self.test_did,
                their_seed=self.test_seed,
                their_endpoint=self.test_endpoint,
            )

            assert ConnRecord.State.get(conn_rec.state) is ConnRecord.State.COMPLETED

    async def test_find_connection_retrieve_by_did(self):
        with async_mock.patch.object(
            ConnRecord, "retrieve_by_did", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_did:
            mock_conn_retrieve_by_did.return_value = async_mock.MagicMock(
                state=ConnRecord.State.RESPONSE.rfc23,
                save=async_mock.CoroutineMock(),
            )

            conn_rec = await self.manager.find_connection(
                their_did=self.test_target_did,
                my_did=self.test_did,
                my_verkey=self.test_verkey,
                auto_complete=True,
            )
            assert ConnRecord.State.get(conn_rec.state) is ConnRecord.State.COMPLETED

    async def test_find_connection_retrieve_by_did_auto_disclose_features(self):
        self.context.update_settings({"auto_disclose_features": True})
        with async_mock.patch.object(
            ConnRecord, "retrieve_by_did", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_did, async_mock.patch.object(
            V20DiscoveryMgr, "proactive_disclose_features", async_mock.CoroutineMock()
        ) as mock_proactive_disclose_features:
            mock_conn_retrieve_by_did.return_value = async_mock.MagicMock(
                state=ConnRecord.State.RESPONSE.rfc23,
                save=async_mock.CoroutineMock(),
            )

            conn_rec = await self.manager.find_connection(
                their_did=self.test_target_did,
                my_did=self.test_did,
                my_verkey=self.test_verkey,
                auto_complete=True,
            )
            assert ConnRecord.State.get(conn_rec.state) is ConnRecord.State.COMPLETED
            mock_proactive_disclose_features.assert_called_once()

    async def test_find_connection_retrieve_by_invitation_key(self):
        with async_mock.patch.object(
            ConnRecord, "retrieve_by_did", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_did, async_mock.patch.object(
            ConnRecord, "retrieve_by_invitation_key", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_invitation_key:
            mock_conn_retrieve_by_did.side_effect = StorageNotFoundError()
            mock_conn_retrieve_by_invitation_key.return_value = async_mock.MagicMock(
                state=ConnRecord.State.RESPONSE,
                save=async_mock.CoroutineMock(),
            )

            conn_rec = await self.manager.find_connection(
                their_did=self.test_target_did,
                my_did=self.test_did,
                my_verkey=self.test_verkey,
            )
            assert conn_rec

    async def test_find_connection_retrieve_none_by_invitation_key(self):
        with async_mock.patch.object(
            ConnRecord, "retrieve_by_did", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_did, async_mock.patch.object(
            ConnRecord, "retrieve_by_invitation_key", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_invitation_key:
            mock_conn_retrieve_by_did.side_effect = StorageNotFoundError()
            mock_conn_retrieve_by_invitation_key.side_effect = StorageNotFoundError()

            conn_rec = await self.manager.find_connection(
                their_did=self.test_target_did,
                my_did=self.test_did,
                my_verkey=self.test_verkey,
            )
            assert conn_rec is None

    async def test_get_endpoints(self):
        conn_id = "dummy"

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_retrieve, async_mock.patch.object(
            InMemoryWallet, "get_local_did", autospec=True
        ) as mock_wallet_get_local_did, async_mock.patch.object(
            self.manager, "get_connection_targets", async_mock.CoroutineMock()
        ) as mock_get_conn_targets:
            mock_retrieve.return_value = async_mock.MagicMock()
            mock_wallet_get_local_did.return_value = async_mock.MagicMock(
                metadata={"endpoint": "localhost:8020"}
            )
            mock_get_conn_targets.return_value = [
                async_mock.MagicMock(endpoint="10.20.30.40:5060")
            ]
            assert await self.manager.get_endpoints(conn_id) == (
                "localhost:8020",
                "10.20.30.40:5060",
            )
