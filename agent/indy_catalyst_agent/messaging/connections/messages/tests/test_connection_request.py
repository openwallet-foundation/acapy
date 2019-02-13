from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from von_anchor.a2a import DIDDoc
from von_anchor.a2a.publickey import PublicKey, PublicKeyType
from von_anchor.a2a.service import Service

from ..connection_request import (
    ConnectionRequest,
    ConnectionRequestSchema,
    ConnectionDetail,
)
from ...message_types import CONNECTION_REQUEST


class TestConfig:
    test_seed = "testseed000000000000000000000001"
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_label = "Label"
    test_endpoint = "http://localhost"

    def make_did_doc(self):
        doc = DIDDoc(did=self.test_did)
        controller = self.test_did
        ident = "1"
        value = self.test_verkey
        pk = PublicKey(
            self.test_did,
            ident,
            PublicKeyType.ED25519_SIG_2018,
            controller,
            value,
            False,
        )
        doc.verkeys.append(pk)
        service = Service(self.test_did, "indy", "IndyAgent", self.test_endpoint)
        doc.services.append(service)
        return doc


class TestConnectionRequest(TestCase, TestConfig):
    def setUp(self):
        self.connection_request = ConnectionRequest(
            connection=ConnectionDetail(did=self.test_did, did_doc=self.make_did_doc()),
            label=self.test_label,
        )

    def test_init(self):
        assert self.connection_request.label == self.test_label
        assert self.connection_request.connection.did == self.test_did
        # assert self.connection_request.verkey == self.verkey

    def test_type(self):
        assert self.connection_request._type == CONNECTION_REQUEST

    @mock.patch(
        "indy_catalyst_agent.messaging.connections.messages.connection_request.ConnectionRequestSchema.load"
    )
    def test_deserialize(self, mock_connection_request_schema_load):
        obj = {"obj": "obj"}

        connection_request = ConnectionRequest.deserialize(obj)
        mock_connection_request_schema_load.assert_called_once_with(obj)

        assert connection_request is mock_connection_request_schema_load.return_value

    @mock.patch(
        "indy_catalyst_agent.messaging.connections.messages.connection_request.ConnectionRequestSchema.dump"
    )
    def test_serialize(self, mock_connection_request_schema_dump):
        connection_request_dict = self.connection_request.serialize()
        mock_connection_request_schema_dump.assert_called_once_with(
            self.connection_request
        )

        assert (
            connection_request_dict is mock_connection_request_schema_dump.return_value
        )


class TestConnectionRequestSchema(AsyncTestCase, TestConfig):
    async def test_make_model(self):
        connection_request = ConnectionRequest(
            connection=ConnectionDetail(did=self.test_did, did_doc=self.make_did_doc()),
            label=self.test_label,
        )
        data = connection_request.serialize()
        model_instance = ConnectionRequest.deserialize(data)
        assert type(model_instance) is type(connection_request)
