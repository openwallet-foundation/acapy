from ..connection_response import ConnectionResponse, ConnectionResponseSchema
from ....message_types import MessageTypes

from unittest import mock, TestCase


class TestConnectionResponse(TestCase):
    endpoint = "endpoint"
    did = "did"
    verkey = "verkey"

    def test_init(self):
        connection_response = ConnectionResponse(
            endpoint=self.endpoint,
            did=self.did,
            verkey=self.verkey
        )
        assert connection_response.endpoint == self.endpoint
        assert connection_response.did == self.did
        assert connection_response.verkey == self.verkey

    def test_type(self):
        connection_response = ConnectionResponse(
            endpoint=self.endpoint,
            did=self.did,
            verkey=self.verkey
        )
        assert connection_response._type == MessageTypes.CONNECTION_RESPONSE.value

    @mock.patch(
        "indy_catalyst_agent.messaging.connections.messages.connection_response.ConnectionResponseSchema.load"
    )
    def test_deserialize(self, mock_connection_response_schema_load):
        obj = {"obj": "obj"}

        connection_response = ConnectionResponse.deserialize(obj)
        mock_connection_response_schema_load.assert_called_once_with(obj)

        assert connection_response is mock_connection_response_schema_load.return_value

    @mock.patch(
        "indy_catalyst_agent.messaging.connections.messages.connection_response.ConnectionResponseSchema.dump"
    )
    def test_serialize(self, mock_connection_response_schema_dump):
        connection_response = ConnectionResponse(
            endpoint=self.endpoint,
            did=self.did,
            verkey=self.verkey
        )

        connection_response_dict = connection_response.serialize()
        mock_connection_response_schema_dump.assert_called_once_with(
            connection_response
        )

        assert (
            connection_response_dict
            is mock_connection_response_schema_dump.return_value
        )


class TestConnectionResponseSchema(TestCase):
    connection_response = ConnectionResponse(
        endpoint="endpoint",
        did="did",
        verkey="verkey"
    )

    def test_make_model(self):
        data = self.connection_response.serialize()
        model_instance = ConnectionResponse.deserialize(data)
        assert type(model_instance) is type(self.connection_response)

