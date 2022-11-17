from asynctest import TestCase as AsyncTestCase

from unittest import mock, TestCase

from .....didcomm_prefix import DIDCommPrefix

from ..invitation_request import InvitationRequest
from ...message_types import INVITATION_REQUEST, PROTOCOL_PACKAGE


class TestConfig:
    test_responder = "RESPONDER"
    test_message = "MESSAGE"


class TestInvitationRequest(TestCase, TestConfig):
    def setUp(self):
        self.request = InvitationRequest(
            responder=self.test_responder, message=self.test_message
        )

    def test_init(self):
        """Test initialization."""
        assert self.request.responder == self.test_responder
        assert self.request.message == self.test_message

    def test_type(self):
        """Test type."""
        assert self.request._type == DIDCommPrefix.qualify_current(INVITATION_REQUEST)

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages."
        "invitation_request.InvitationRequestSchema.load"
    )
    def test_deserialize(self, mock_invitation_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        request = InvitationRequest.deserialize(obj)
        mock_invitation_schema_load.assert_called_once_with(obj)

        assert request is mock_invitation_schema_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages."
        "invitation_request.InvitationRequestSchema.dump"
    )
    def test_serialize(self, mock_invitation_schema_dump):
        """
        Test serialization.
        """
        request_dict = self.request.serialize()
        mock_invitation_schema_dump.assert_called_once_with(self.request)

        assert request_dict is mock_invitation_schema_dump.return_value


class TestInvitationRequestSchema(AsyncTestCase, TestConfig):
    """Test invitation request schema."""

    async def test_make_model(self):
        request = InvitationRequest(
            responder=self.test_responder, message=self.test_message
        )
        data = request.serialize()
        model_instance = InvitationRequest.deserialize(data)
        assert type(model_instance) is type(request)
