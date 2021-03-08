from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from ......connections.models.diddoc_v2 import (
    DIDDoc,
    VerificationMethod,
    PublicKeyType,
    Service,
)

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CONNECTION_REQUEST
from ...models.connection_detail import ConnectionDetail

from ..connection_request import ConnectionRequest


class TestConfig:
    test_seed = "testseed000000000000000000000001"
    test_did = "did:sov:55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_label = "Label"
    test_endpoint = "http://localhost"

    def make_did_doc(self):
        did = self.test_did
        verkey = self.test_verkey
        endpoint = self.test_endpoint
        doc = DIDDoc(did)

        pk = doc.add_verification_method(
            type=PublicKeyType.ED25519_SIG_2018, controller=did, value=verkey, ident="1"
        )

        doc.add_didcomm_service(
            type="IndyAgent", recipient_keys=[pk], routing_keys=[], endpoint=endpoint
        )
        return doc


class TestConnectionRequest(TestCase, TestConfig):
    def setUp(self):
        self.connection_request = ConnectionRequest(
            connection=ConnectionDetail(did=self.test_did, did_doc=self.make_did_doc()),
            label=self.test_label,
        )

    def test_init(self):
        """Test initialization."""
        assert self.connection_request.label == self.test_label
        assert self.connection_request.connection.did == self.test_did
        # assert self.connection_request.verkey == self.verkey

    def test_type(self):
        """Test type."""
        assert self.connection_request._type == DIDCommPrefix.qualify_current(
            CONNECTION_REQUEST
        )

    @mock.patch(
        "aries_cloudagent.protocols.connections.v1_0.messages."
        "connection_request.ConnectionRequestSchema.load"
    )
    def test_deserialize(self, mock_connection_request_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        connection_request = ConnectionRequest.deserialize(obj)
        mock_connection_request_schema_load.assert_called_once_with(obj)

        assert connection_request is mock_connection_request_schema_load.return_value

    @mock.patch(
        "aries_cloudagent.protocols.connections.v1_0.messages."
        "connection_request.ConnectionRequestSchema.dump"
    )
    def test_serialize(self, mock_connection_request_schema_dump):
        """
        Test serialization.
        """
        connection_request_dict = self.connection_request.serialize()
        mock_connection_request_schema_dump.assert_called_once_with(
            self.connection_request
        )

        assert (
            connection_request_dict is mock_connection_request_schema_dump.return_value
        )


class TestConnectionRequestSchema(AsyncTestCase, TestConfig):
    """Test connection request schema."""

    async def test_make_model(self):
        connection_request = ConnectionRequest(
            connection=ConnectionDetail(did=self.test_did, did_doc=self.make_did_doc()),
            label=self.test_label,
        )
        data = connection_request.serialize()
        model_instance = ConnectionRequest.deserialize(data)
        assert type(model_instance) is type(connection_request)

    async def test_make_model_conn_detail_interpolate_authn_service(self):
        did_doc_dict = self.make_did_doc().serialize()
        del did_doc_dict["service"]
        did_doc = DIDDoc.deserialize(did_doc_dict)

        connection_request = ConnectionRequest(
            connection=ConnectionDetail(did=self.test_did, did_doc=did_doc),
            label=self.test_label,
        )
        data = connection_request.serialize()
        model_instance = ConnectionRequest.deserialize(data)
        assert type(model_instance) is type(connection_request)
