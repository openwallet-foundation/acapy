from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from .....connections.v1_0.messages.connection_invitation import ConnectionInvitation
from .....didcomm_prefix import DIDCommPrefix

from ...message_types import FORWARD_INVITATION, PROTOCOL_PACKAGE

from ..forward_invitation import ForwardInvitation


class TestConfig:
    label = "Label"
    did = "did:sov:QmWbsNYhMrjHiqZDTUTEJs"
    endpoint_url = "https://example.com/endpoint"
    endpoint_did = "did:sov:A2wBhNYhMrjHiqZDTUYH7u"
    key = "8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"
    test_message = "test message"


class TestForwardInvitation(TestCase, TestConfig):
    def setUp(self):
        self.connection_invitation = ConnectionInvitation(
            label=self.label, recipient_keys=[self.key], endpoint=self.endpoint_url
        )
        self.invitation = ForwardInvitation(
            invitation=self.connection_invitation, message=self.test_message
        )

    def test_init(self):
        """Test initialization."""
        assert self.invitation.invitation == self.connection_invitation
        assert self.invitation.message == self.test_message

    def test_type(self):
        """Test type."""
        assert self.invitation._type == DIDCommPrefix.qualify_current(
            FORWARD_INVITATION
        )

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages."
        "forward_invitation.ForwardInvitationSchema.load"
    )
    def test_deserialize(self, mock_invitation_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        invitation = ForwardInvitation.deserialize(obj)
        mock_invitation_schema_load.assert_called_once_with(obj)

        assert invitation is mock_invitation_schema_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages."
        "forward_invitation.ForwardInvitationSchema.dump"
    )
    def test_serialize(self, mock_invitation_schema_dump):
        """
        Test serialization.
        """
        invitation_dict = self.invitation.serialize()
        mock_invitation_schema_dump.assert_called_once_with(self.invitation)

        assert invitation_dict is mock_invitation_schema_dump.return_value


class TestForwardInvitationSchema(AsyncTestCase, TestConfig):
    """Test forward invitation schema."""

    async def test_make_model(self):
        invitation = ForwardInvitation(
            invitation=ConnectionInvitation(
                label=self.label, recipient_keys=[self.key], endpoint=self.endpoint_url
            ),
            message=self.test_message,
        )
        data = invitation.serialize()
        model_instance = ForwardInvitation.deserialize(data)
        assert type(model_instance) is type(invitation)
