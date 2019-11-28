from asynctest import TestCase as AsyncTestCase

from ...config.injection_context import InjectionContext
from ...protocols.connections.messages.connection_invitation import (
    ConnectionInvitation
)
from ...protocols.connections.messages.connection_request import ConnectionRequest
from ...protocols.connections.models.connection_detail import ConnectionDetail
from ...storage.base import BaseStorage
from ...storage.basic import BasicStorage

from ..models.connection_record import ConnectionRecord
from ..models.diddoc import DIDDoc


class TestConfig:

    test_seed = "testseed000000000000000000000001"
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_endpoint = "http://localhost"

    test_target_did = "GbuDUYXaUZRfHD2jeDuQuP"
    test_target_verkey = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"

    test_did_doc = DIDDoc.deserialize(
        {
            "@context": "https://w3id.org/did/v1",
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "authentication": [
                {
                    "id": "LjgpST2rjsoxYegQDRm7EL#keys-1",
                    "type": "Ed25519VerificationKey2018",
                    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyBase58": "~XXXXXXXXXXXXXXXX",
                }
            ],
            "service": [
                {
                    "type": "DidMessaging",
                    "serviceEndpoint": "https://example.com/endpoint/8377464",
                }
            ],
        }
    )


class TestConnectionRecord(AsyncTestCase, TestConfig):
    def setUp(self):
        self.storage = BasicStorage()
        self.context = InjectionContext()
        self.context.injector.bind_instance(BaseStorage, self.storage)
        self.test_info = ConnectionRecord(
            my_did=self.test_did,
            their_did=self.test_target_did,
            their_role=None,
            state=ConnectionRecord.STATE_ACTIVE,
        )

    async def test_save_retrieve_compare(self):
        record = ConnectionRecord(my_did=self.test_did)
        record_id = await record.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_id(self.context, record_id)
        assert fetched and fetched == record

        bad_record = ConnectionRecord(my_did=None)
        assert bad_record != record

        assert fetched == await ConnectionRecord.retrieve_by_did(
            context=self.context,
            their_did=None,
            my_did=self.test_did,
            initiator=None,
        )

        record_pairwise = ConnectionRecord(
            my_did=self.test_did,
            their_did=self.test_target_did,
        )
        await record_pairwise.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_did(
            context=self.context,
            their_did=self.test_target_did,
            my_did=self.test_did,
            initiator=None
        )
        assert fetched and fetched == record_pairwise

        record_pairwise_initiator = ConnectionRecord(
            my_did=self.test_target_did,
            their_did=self.test_did,
            initiator=ConnectionRecord.INITIATOR_MULTIUSE,
            invitation_key=self.test_verkey,
            request_id="dummy",
            state=ConnectionRecord.STATE_INVITATION,
        )
        await record_pairwise_initiator.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_did(
            context=self.context,
            their_did=self.test_did,
            my_did=self.test_target_did,
            initiator=ConnectionRecord.INITIATOR_MULTIUSE,
        )
        assert fetched and fetched == record_pairwise_initiator
        assert fetched == await ConnectionRecord.retrieve_by_invitation_key(
            context=self.context,
            invitation_key=self.test_verkey,
            initiator=ConnectionRecord.INITIATOR_MULTIUSE,
        )
        assert fetched == await ConnectionRecord.retrieve_by_request_id(
            context=self.context,
            request_id="dummy",
        )

        await record.delete_record(self.context)
        await record_pairwise.delete_record(self.context)
        await record_pairwise_initiator.delete_record(self.context)

    async def test_attach_retrieve(self):
        invitation = ConnectionInvitation(
            label="dummy",
            did=None,
            recipient_keys=[self.test_verkey],
            endpoint=self.test_endpoint,
            routing_keys=[self.test_verkey],
            image_url=None,
        )
        record = ConnectionRecord(
            my_did=self.test_target_did,
            their_did=self.test_did,
            initiator=ConnectionRecord.INITIATOR_MULTIUSE,
            invitation_key=self.test_verkey,
            request_id="dummy",
        )
        await record.save(self.context)
        await record.attach_invitation(self.context, invitation)
        assert (
            await record.retrieve_invitation(self.context)
        )._message_id == invitation._message_id

        conn_detail = ConnectionDetail(did=self.test_did, did_doc=self.test_did_doc)
        request = ConnectionRequest(
            connection=conn_detail,
            label="Hello",
            image_url=None,
        )
        await record.attach_request(self.context, request)
        assert (
            await record.retrieve_request(self.context)
        )._message_id == request._message_id

    async def test_active_is_ready(self):
        record = ConnectionRecord(
            my_did=self.test_did, state=ConnectionRecord.STATE_ACTIVE
        )
        record_id = await record.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_id(self.context, record_id)

        assert fetched.is_ready == True

    async def test_response_is_ready(self):
        record = ConnectionRecord(
            my_did=self.test_did, state=ConnectionRecord.STATE_RESPONSE
        )
        record_id = await record.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_id(self.context, record_id)

        assert fetched.is_ready is True

    async def test_request_is_not_ready(self):
        record = ConnectionRecord(
            my_did=self.test_did, state=ConnectionRecord.STATE_REQUEST
        )
        record_id = await record.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_id(self.context, record_id)

        assert fetched.is_ready is False

    async def test_invitation_is_not_multi_use(self):
        record = ConnectionRecord(
            my_did=self.test_did,
            state=ConnectionRecord.STATE_INVITATION,
            invitation_mode=ConnectionRecord.INVITATION_MODE_ONCE,
        )
        record_id = await record.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_id(self.context, record_id)

        assert fetched.is_multiuse_invitation is False

    async def test_invitation_is_multi_use(self):
        record = ConnectionRecord(
            my_did=self.test_did,
            state=ConnectionRecord.STATE_INVITATION,
            invitation_mode=ConnectionRecord.INVITATION_MODE_MULTI,
        )
        record_id = await record.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_id(self.context, record_id)

        assert fetched.is_multiuse_invitation is True
