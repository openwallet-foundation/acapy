from unittest import mock, TestCase
from peerdid.dids import resolve_peer_did
from asynctest import TestCase as AsyncTestCase

from ......wallet.key_type import ED25519
from ......connections.models.diddoc import (
    LegacyDIDDoc,
    PublicKey,
    PublicKeyType,
    Service,
)
from ......core.in_memory import InMemoryProfile

from .....didcomm_prefix import DIDCommPrefix
from ...message_types import CONNECTION_RESPONSE
from ...models.connection_detail import ConnectionDetail

from ..connection_response import ConnectionResponse


class TestConfig:
    test_seed = "testseed000000000000000000000001"
    test_did = "did:peer:2.Ez6LSpkcni2KTTxf4nAp6cPxjRbu26Tj4b957BgHcknVeNFEj.Vz6MksXhfmxm2i3RnoHH2mKQcx7EY4tToJR9JziUs6bp8a6FM.SeyJ0IjoiZGlkLWNvbW11bmljYXRpb24iLCJzIjoiaHR0cDovL2hvc3QuZG9ja2VyLmludGVybmFsOjkwNzAiLCJyZWNpcGllbnRfa2V5cyI6W119"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_endpoint = "http://localhost"

    def make_did_doc(self):
        return resolve_peer_did(self.test_did)

class TestConnectionResponse(TestCase, TestConfig):
    def setUp(self):
        self.connection_response = ConnectionResponse(
            connection=ConnectionDetail(did=self.test_did, did_doc=self.make_did_doc())
        )

    def test_init(self):
        assert self.connection_response.connection.did == self.test_did

    def test_type(self):
        assert self.connection_response._type == DIDCommPrefix.qualify_current(
            CONNECTION_RESPONSE
        )

    @mock.patch(
        "aries_cloudagent.protocols.connections.v1_0.messages."
        "connection_response.ConnectionResponseSchema.load"
    )
    def test_deserialize(self, mock_connection_response_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        connection_response = ConnectionResponse.deserialize(obj)
        mock_connection_response_schema_load.assert_called_once_with(obj)

        assert connection_response is mock_connection_response_schema_load.return_value

    @mock.patch(
        "aries_cloudagent.protocols.connections.v1_0.messages."
        "connection_response.ConnectionResponseSchema.dump"
    )
    def test_serialize(self, mock_connection_response_schema_dump):
        """
        Test serialization.
        """
        connection_response_dict = self.connection_response.serialize()
        mock_connection_response_schema_dump.assert_called_once_with(
            self.connection_response
        )

        assert (
            connection_response_dict
            is mock_connection_response_schema_dump.return_value
        )


class TestConnectionResponseSchema(AsyncTestCase, TestConfig):
    async def test_make_model(self):
        connection_response = ConnectionResponse(
            connection=ConnectionDetail(did=self.test_did, did_doc=self.make_did_doc())
        )
        session = InMemoryProfile.test_session()
        wallet = session.wallet
        key_info = await wallet.create_signing_key(ED25519)
        await connection_response.sign_field("connection", key_info.verkey, wallet)
        data = connection_response.serialize()
        model_instance = ConnectionResponse.deserialize(data)
        assert type(model_instance) is type(connection_response)
