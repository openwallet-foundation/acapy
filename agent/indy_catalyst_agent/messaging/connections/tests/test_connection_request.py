from ..connection_request import ConnectionRequest, ConnectionRequestSchema
from ...message_types import MessageTypes

from unittest import mock, TestCase


class TestConnectionRequest(TestCase):
    endpoint = "endpoint"
    did = "did"
    verkey = "verkey"

    def test_init(self):
        connection_request = ConnectionRequest(self.endpoint, self.did, self.verkey)
        assert connection_request.endpoint == self.endpoint
        assert connection_request.did == self.did
        assert connection_request.verkey == self.verkey

    def test_type(self):
        connection_request = ConnectionRequest(self.endpoint, self.did, self.verkey)
        assert connection_request._type == MessageTypes.CONNECTION_REQUEST.value

    @mock.patch(
        "indy_catalyst_agent.messaging.connections.connection_request.ConnectionRequestSchema.load"
    )
    def test_deserialize(self, mock_connection_request_schema_load):
        obj = {"obj": "obj"}

        connection_request = ConnectionRequest.deserialize(obj)
        mock_connection_request_schema_load.assert_called_once_with(obj)

        assert connection_request is mock_connection_request_schema_load.return_value

    @mock.patch(
        "indy_catalyst_agent.messaging.connections.connection_request.ConnectionRequestSchema.dump"
    )
    def test_serialize(self, mock_connection_request_schema_dump):
        connection_request = ConnectionRequest(self.endpoint, self.did, self.verkey)

        connection_request_dict = connection_request.serialize()
        mock_connection_request_schema_dump.assert_called_once_with(connection_request)

        assert (
            connection_request_dict is mock_connection_request_schema_dump.return_value
        )


class TestConnectionRequestSchema(TestCase):
    connection_request = ConnectionRequest("endpoint", "did", "verkey")

    def test_make_model(self):
        schema = ConnectionRequestSchema()

        data = self.connection_request.serialize()
        data["_type"] = data["@type"]
        del data["@type"]

        model_instance = schema.make_model(data)
        assert type(model_instance) is type(self.connection_request)

