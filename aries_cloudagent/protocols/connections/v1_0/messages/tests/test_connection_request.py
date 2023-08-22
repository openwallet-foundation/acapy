from unittest import mock, TestCase
from peerdid.dids import resolve_peer_did
from asynctest import TestCase as AsyncTestCase

from ......connections.models.diddoc import (
    LegacyDIDDoc,
    PublicKey,
    PublicKeyType,
    Service,
)

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CONNECTION_REQUEST
from ...models.connection_detail import ConnectionDetail

from ..connection_request import ConnectionRequest


class TestConfig:
    test_seed = "testseed000000000000000000000001"
    test_did = "did:peer:2.Ez6LSpkcni2KTTxf4nAp6cPxjRbu26Tj4b957BgHcknVeNFEj.Vz6MksXhfmxm2i3RnoHH2mKQcx7EY4tToJR9JziUs6bp8a6FM.SeyJ0IjoiZGlkLWNvbW11bmljYXRpb24iLCJzIjoiaHR0cDovL2hvc3QuZG9ja2VyLmludGVybmFsOjkwNzAiLCJyZWNpcGllbnRfa2V5cyI6W119"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_label = "Label"
    test_endpoint = "http://localhost"

    def make_did_doc(self):
        return resolve_peer_did(self.test_did)


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
