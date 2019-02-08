from ..connection_invitation import ConnectionInvitation
from ....message_types import MessageTypes

from unittest import mock, TestCase


class TestConnectionInvitation(TestCase):
    label = "label"
    did = "did:sov:QmWbsNYhMrjHiqZDTUTEJs"
    endpoint_url = "https://example.com/endpoint"
    endpoint_did = "did:sov:A2wBhNYhMrjHiqZDTUYH7u"
    image_url = "https://example.com/image.jpg"
    key = "8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"

    def test_init(self):
        connection_invitation = ConnectionInvitation(
            label=self.label,
            did=self.did,
            key=self.key,
            endpoint=self.endpoint_url,
            image_url=self.image_url,
        )
        assert connection_invitation.label == self.label
        assert connection_invitation.did == self.did
        assert connection_invitation.key == self.key
        assert connection_invitation.endpoint == self.endpoint_url
        assert connection_invitation.image_url == self.image_url

    def test_type(self):
        connection_invitation = ConnectionInvitation(
            label=self.label,
            did=self.did,
            key=self.key,
            endpoint=self.endpoint_url,
            image_url=self.image_url,
        )

        assert connection_invitation._type == MessageTypes.CONNECTION_INVITATION.value

    @mock.patch(
        "indy_catalyst_agent.messaging.connections.messages.connection_invitation.ConnectionInvitationSchema.load"
    )
    def test_deserialize(self, mock_connection_invitation_schema_load):
        obj = {"obj": "obj"}

        connection_invitation = ConnectionInvitation.deserialize(obj)
        mock_connection_invitation_schema_load.assert_called_once_with(obj)

        assert (
            connection_invitation is mock_connection_invitation_schema_load.return_value
        )

    @mock.patch(
        "indy_catalyst_agent.messaging.connections.messages.connection_invitation.ConnectionInvitationSchema.dump"
    )
    def test_serialize(self, mock_connection_invitation_schema_dump):
        connection_invitation = ConnectionInvitation(
            label=self.label,
            did=self.did,
            key=self.key,
            endpoint=self.endpoint_url,
            image_url=self.image_url,
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
        label="label",
        did="did:sov:QmWbsNYhMrjHiqZDTUTEJs"
    )

    def test_make_model(self):
        data = self.connection_invitation.serialize()
        model_instance = ConnectionInvitation.deserialize(data)
        assert type(model_instance) is type(self.connection_invitation)
