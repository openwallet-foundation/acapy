from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase

from ..mediation_grant import MediationGrant
from ...message_types import MEDIATION_GRANT, PROTOCOL_PACKAGE

test_endpoint = "dummy"
test_routing_keys = ["dummy","dummy"]

class TestMediationGrant(TestCase):
    def setUp(self):
        self.test_message = MediationGrant(endpoint=test_endpoint, routing_keys=test_routing_keys)

    def test_init(self):
        """Test initialization."""
        assert self.test_message.endpoint == test_endpoint
        assert self.test_message.routing_keys == test_routing_keys

    def test_type(self):
        """Test type."""
        assert self.test_message._type == MEDIATION_GRANT

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.mediation_grant.MediationGrantSchema.load")
    def test_deserialize(self, mock_mediation_grant_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        msg = MediationGrant.deserialize(obj)
        mock_mediation_grant_schema_load.assert_called_once_with(obj)

        assert msg is mock_mediation_grant_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.mediation_grant.MediationGrantSchema.dump")
    def test_serialize(self, mock_mediation_grant_schema_load):
        """
        Test serialization.
        """
        msg_dict = self.test_message.serialize()
        mock_mediation_grant_schema_load.assert_called_once_with(self.test_message)

        assert msg_dict is mock_mediation_grant_schema_load.return_value


class TestMediationGrantSchema(AsyncTestCase):
    """Test mediation grant schema."""

    async def test_make_model(self):
        mediation_grant = MediationGrant(endpoint=test_endpoint, routing_keys=test_routing_keys)
        data = mediation_grant.serialize()
        model_instance = MediationGrant.deserialize(data)
        assert type(model_instance) is type(mediation_grant)