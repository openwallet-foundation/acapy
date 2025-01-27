from unittest import IsolatedAsyncioTestCase, TestCase, mock

from ......did.did_key import DIDKey
from ......wallet.key_type import ED25519
from .....didcomm_prefix import DIDCommPrefix
from .....out_of_band.v1_0.messages.invitation import InvitationMessage, Service
from ...message_types import FORWARD_INVITATION, PROTOCOL_PACKAGE
from ..forward_invitation import ForwardInvitation


class TestConfig:
    label = "Label"
    did = "did:sov:QmWbsNYhMrjHiqZDTUTEJs"
    endpoint_url = "https://example.com/endpoint"
    endpoint_did = "did:sov:A2wBhNYhMrjHiqZDTUYH7u"
    key = "8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"
    did_key = DIDKey.from_public_key_b58(key, ED25519)
    test_message = "test message"


class TestForwardInvitation(TestCase, TestConfig):
    def setUp(self):
        self.service = Service(
            recipient_keys=[self.key], service_endpoint=self.endpoint_url
        )
        self.connection_invitation = InvitationMessage(
            label=self.label, services=[self.service]
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
        assert self.invitation._type == DIDCommPrefix.qualify_current(FORWARD_INVITATION)

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.forward_invitation.ForwardInvitationSchema.load"
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
        f"{PROTOCOL_PACKAGE}.messages.forward_invitation.ForwardInvitationSchema.dump"
    )
    def test_serialize(self, mock_invitation_schema_dump):
        """
        Test serialization.
        """
        invitation_dict = self.invitation.serialize()
        mock_invitation_schema_dump.assert_called_once_with(self.invitation)

        assert invitation_dict is mock_invitation_schema_dump.return_value


class TestForwardInvitationSchema(IsolatedAsyncioTestCase, TestConfig):
    """Test forward invitation schema."""

    async def test_make_model(self):
        service = Service(
            _id="asdf",
            _type="did-communication",
            recipient_keys=[self.did_key.did],
            service_endpoint=self.endpoint_url,
        )
        invitation = ForwardInvitation(
            invitation=InvitationMessage(
                label=self.label,
                services=[service],
                handshake_protocols=["didexchange/1.1"],
            ),
            message=self.test_message,
        )
        data = invitation.serialize()
        model_instance = ForwardInvitation.deserialize(data)
        assert type(model_instance) is type(invitation)
