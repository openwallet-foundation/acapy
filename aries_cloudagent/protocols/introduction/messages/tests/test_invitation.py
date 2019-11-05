from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase

from ....connections.messages.connection_invitation import ConnectionInvitation

from ..invitation import Invitation
from ...message_types import INVITATION, PROTOCOL_PACKAGE


class TestConfig:
    label = "Label"
    did = "did:sov:QmWbsNYhMrjHiqZDTUTEJs"
    endpoint_url = "https://example.com/endpoint"
    endpoint_did = "did:sov:A2wBhNYhMrjHiqZDTUYH7u"
    key = "8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"
    test_message = "test message"


class TestInvitation(TestCase, TestConfig):
    def setUp(self):
        self.connection_invitation = ConnectionInvitation(
            label=self.label, recipient_keys=[self.key], endpoint=self.endpoint_url
        )
        self.invitation = Invitation(
            invitation=self.connection_invitation, message=self.test_message
        )

    def test_init(self):
        """Test initialization."""
        assert self.invitation.invitation == self.connection_invitation
        assert self.invitation.message == self.test_message

    def test_type(self):
        """Test type."""
        assert self.invitation._type == INVITATION

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.invitation.InvitationSchema.load")
    def test_deserialize(self, mock_invitation_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        invitation = Invitation.deserialize(obj)
        mock_invitation_schema_load.assert_called_once_with(obj)

        assert invitation is mock_invitation_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.invitation.InvitationSchema.dump")
    def test_serialize(self, mock_invitation_schema_dump):
        """
        Test serialization.
        """
        invitation_dict = self.invitation.serialize()
        mock_invitation_schema_dump.assert_called_once_with(self.invitation)

        assert invitation_dict is mock_invitation_schema_dump.return_value


class TestInvitationSchema(AsyncTestCase, TestConfig):
    """Test invitation schema."""

    async def test_make_model(self):
        invitation = Invitation(
            invitation=ConnectionInvitation(
                label=self.label, recipient_keys=[self.key], endpoint=self.endpoint_url
            ),
            message=self.test_message,
        )
        data = invitation.serialize()
        model_instance = Invitation.deserialize(data)
        assert type(model_instance) is type(invitation)
