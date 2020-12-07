from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from ......connections.models.diddoc import (
    DIDDoc,
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
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_endpoint = "http://localhost"

    def make_did_doc(self):
        doc = DIDDoc(did=self.test_did)
        controller = self.test_did
        ident = "1"
        pk_value = self.test_verkey
        pk = PublicKey(
            self.test_did,
            ident,
            pk_value,
            PublicKeyType.ED25519_SIG_2018,
            controller,
            False,
        )
        doc.set(pk)
        recip_keys = [pk]
        routing_keys = []
        service = Service(
            self.test_did,
            "indy",
            "IndyAgent",
            recip_keys,
            routing_keys,
            self.test_endpoint,
        )
        doc.set(service)
        return doc


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
        key_info = await wallet.create_signing_key()
        await connection_response.sign_field("connection", key_info.verkey, wallet)
        data = connection_response.serialize()
        model_instance = ConnectionResponse.deserialize(data)
        assert type(model_instance) is type(connection_response)
