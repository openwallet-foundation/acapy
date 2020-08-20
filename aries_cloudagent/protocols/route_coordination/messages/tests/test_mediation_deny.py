from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase

from ..mediation_deny import MediationDeny
from ...message_types import MEDIATION_DENY, PROTOCOL_PACKAGE

test_mediator_terms = ["dummy","dummy"]
test_recipient_terms = ["dummy","dummy"]

class TestMediationDeny(TestCase):
    def setUp(self):
        self.test_message = MediationDeny(mediator_terms=test_mediator_terms, recipient_terms=test_recipient_terms)

    def test_init(self):
        """Test initialization."""
        assert self.test_message.mediator_terms == test_mediator_terms
        assert self.test_message.recipient_terms == test_recipient_terms

    def test_type(self):
        """Test type."""
        assert self.test_message._type == MEDIATION_DENY

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.mediation_deny.MediationDenySchema.load")
    def test_deserialize(self, mock_mediation_deny_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        msg = MediationDeny.deserialize(obj)
        mock_mediation_deny_schema_load.assert_called_once_with(obj)

        assert msg is mock_mediation_deny_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.mediation_deny.MediationDenySchema.dump")
    def test_serialize(self, mock_mediation_deny_schema_load):
        """
        Test serialization.
        """
        msg_dict = self.test_message.serialize()
        mock_mediation_deny_schema_load.assert_called_once_with(self.test_message)

        assert msg_dict is mock_mediation_deny_schema_load.return_value


class TestMediationDenySchema(AsyncTestCase):
    """Test mediation deny schema."""

    async def test_make_model(self):
        mediation_deny = MediationDeny(mediator_terms=test_mediator_terms, recipient_terms=test_recipient_terms)
        data = mediation_deny.serialize()
        model_instance = MediationDeny.deserialize(data)
        assert type(model_instance) is type(mediation_deny)