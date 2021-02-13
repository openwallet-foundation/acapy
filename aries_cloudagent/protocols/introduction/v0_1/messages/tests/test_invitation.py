from asynctest import TestCase as AsyncTestCase

from unittest import mock, TestCase

from ......wallet.util import naked_to_did_key
from .....out_of_band.v1_0.message_types import INVITATION as OOB_INVITATION
from .....out_of_band.v1_0.messages.invitation import (
    HSProto,
    InvitationMessage as OOBInvitationMessage,
)
from .....out_of_band.v1_0.messages.service import Service as OOBService
from .....didcomm_prefix import DIDCommPrefix

from ..invitation import Invitation as IntroInvitation
from ...message_types import INVITATION as INTRO_INVITATION, PROTOCOL_PACKAGE


class TestInvitation(AsyncTestCase):
    def setUp(self):
        self.label = "Label"
        self.test_did = "55GkHamhTU1ZbTbV2ab9DE"
        self.did = "did:sov:QmWbsNYhMrjHiqZDTUTEJs"
        self.endpoint_url = "https://example.com/endpoint"
        self.endpoint_did = "did:sov:A2wBhNYhMrjHiqZDTUYH7u"
        self.key = "8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"
        self.test_message = "test message"

        self.oob_invi_msg = OOBInvitationMessage(
            label=self.label,
            handshake_protocols=[DIDCommPrefix.qualify_current(HSProto.RFC23.name)],
            service=[
                OOBService(
                    _id="#inline",
                    _type="did-communication",
                    did=self.test_did,
                    recipient_keys=[naked_to_did_key(self.key)],
                    service_endpoint=self.endpoint_url,
                )
            ],
        )
        self.intro_invitation = IntroInvitation(
            invitation=self.oob_invi_msg, message=self.test_message
        )

    def test_init(self):
        """Test initialization."""
        assert self.intro_invitation.invitation == self.oob_invi_msg
        assert self.intro_invitation.message == self.test_message

    def test_type(self):
        """Test type."""
        assert self.intro_invitation._type == DIDCommPrefix.qualify_current(
            INTRO_INVITATION
        )

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.invitation.InvitationSchema.load")
    def test_deserialize(self, mock_invitation_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        intro_invi = IntroInvitation.deserialize(obj)
        mock_invitation_schema_load.assert_called_once_with(obj)

        assert intro_invi is mock_invitation_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.invitation.InvitationSchema.dump")
    def test_serialize(self, mock_invitation_schema_dump):
        """
        Test serialization.
        """
        intro_invi_dict = self.intro_invitation.serialize()
        mock_invitation_schema_dump.assert_called_once_with(self.intro_invitation)

        assert intro_invi_dict is mock_invitation_schema_dump.return_value

    async def test_make_model(self):
        intro_invi = IntroInvitation(
            invitation=self.oob_invi_msg,
            message=self.test_message,
        )

        data = intro_invi.serialize()
        model_instance = IntroInvitation.deserialize(data)
        assert type(model_instance) is type(intro_invi)
