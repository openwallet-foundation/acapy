from ..connection_invitation import ConnectionInvitation, ConnectionInvitationSchema
from ...message_types import MessageTypes

from unittest import mock, TestCase


class TestConnectionInvitation(TestCase):
    endpoint = "endpoint"
    image_url = "image_url"
    connection_key = "connection_key"

    def test_init(self):
        connection_invitation = ConnectionInvitation(
            self.endpoint, self.image_url, self.connection_key
        )
        assert connection_invitation.endpoint == self.endpoint
        assert connection_invitation.image_url == self.image_url
        assert connection_invitation.connection_key == self.connection_key

    def test_type(self):
        connection_invitation = ConnectionInvitation(
            self.endpoint, self.image_url, self.connection_key
        )

        assert connection_invitation._type == MessageTypes.CONNECTION_INVITATION.value

    @mock.patch(
        "indy_catalyst_agent.messages.connections.connection_invitation.ConnectionInvitationSchema.load"
    )
    def test_deserialize(self, mock_connection_invitation_schema_load):
        obj = {"obj": "obj"}

        connection_invitation = ConnectionInvitation.deserialize(obj)
        mock_connection_invitation_schema_load.assert_called_once_with(obj)

        assert (
            connection_invitation is mock_connection_invitation_schema_load.return_value
        )

    @mock.patch(
        "indy_catalyst_agent.messages.connections.connection_invitation.ConnectionInvitationSchema.dump"
    )
    def test_serialize(self, mock_connection_invitation_schema_dump):
        connection_invitation = ConnectionInvitation(
            self.endpoint, self.image_url, self.connection_key
        )

        connection_invitation_dict = connection_invitation.serialize()
        mock_connection_invitation_schema_dump.assert_called_once_with(
            connection_invitation
        )

        assert (
            connection_invitation_dict
            is mock_connection_invitation_schema_dump.return_value
        )


class TestConnectionInvitationSchema(TestCase):
    connection_invitation = ConnectionInvitation(
        "endpoint", "image_url", "connection_key"
    )

    def test_make_model(self):
        schema = ConnectionInvitationSchema()

        data = self.connection_invitation.serialize()
        data["_type"] = data["@type"]
        del data["@type"]

        model_instance = schema.make_model(data)
        assert type(model_instance) is type(self.connection_invitation)

