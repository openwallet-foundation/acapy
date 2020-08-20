from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase

from ..mediation_request import MediationRequest
from ...message_types import MEDIATION_REQUEST, PROTOCOL_PACKAGE

test_mediator_terms = ["dummy","dummy"]
test_recipient_terms = ["dummy","dummy"]

class TestMediationRequest(TestCase):
    def setUp(self):
        self.test_message = MediationRequest(mediator_terms=test_mediator_terms, recipient_terms=test_recipient_terms)

    def test_init(self):
        """Test initialization."""
        assert self.test_message.mediator_terms == test_mediator_terms
        assert self.test_message.recipient_terms == test_recipient_terms

    def test_type(self):
        """Test type."""
        assert self.test_message._type == MEDIATION_REQUEST

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.mediation_request.MediationRequestSchema.load")
    def test_deserialize(self, mock_mediation_request_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        msg = MediationRequest.deserialize(obj)
        mock_mediation_request_schema_load.assert_called_once_with(obj)

        assert msg is mock_mediation_request_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.mediation_request.MediationRequestSchema.dump")
    def test_serialize(self, mock_mediation_request_schema_load):
        """
        Test serialization.
        """
        msg_dict = self.test_message.serialize()
        mock_mediation_request_schema_load.assert_called_once_with(self.test_message)

        assert msg_dict is mock_mediation_request_schema_load.return_value


class TestMediationRequestSchema(AsyncTestCase):
    """Test mediation request schema."""

    async def test_make_model(self):
        mediation_request = MediationRequest(mediator_terms=test_mediator_terms, recipient_terms=test_recipient_terms)
        data = mediation_request.serialize()
        model_instance = MediationRequest.deserialize(data)
        assert type(model_instance) is type(mediation_request)