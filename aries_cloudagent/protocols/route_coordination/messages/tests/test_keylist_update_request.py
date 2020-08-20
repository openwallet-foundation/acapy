from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase

from ..inner.keylist_update_rule import KeylistUpdateRule
from ..keylist_update_request import KeylistUpdateRequest
from ...message_types import KEYLIST_UPDATE, PROTOCOL_PACKAGE

test_recipient_key_data = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
test_action_data = "add"
test_updates = KeylistUpdateRule(recipient_key=test_recipient_key_data, action=test_action_data)

class TestKeylistUpdateRequest(TestCase):
    def setUp(self):
        self.test_message = KeylistUpdateRequest()
        self.test_message.updates.append(test_updates)

    def test_init(self):
        """Test initialization."""
        assert self.test_message.updates[0] == test_updates

    def test_type(self):
        """Test type."""
        assert self.test_message._type == KEYLIST_UPDATE

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.keylist_update_request.KeylistUpdateRequestSchema.load")
    def test_deserialize(self, mock_keylist_update_request_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        msg = KeylistUpdateRequest.deserialize(obj)
        mock_keylist_update_request_schema_load.assert_called_once_with(obj)

        assert msg is mock_keylist_update_request_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.keylist_update_request.KeylistUpdateRequestSchema.dump")
    def test_serialize(self, mock_keylist_update_request_schema_load):
        """
        Test serialization.
        """
        msg_dict = self.test_message.serialize()
        mock_keylist_update_request_schema_load.assert_called_once_with(self.test_message)

        assert msg_dict is mock_keylist_update_request_schema_load.return_value


class TestKeylistUpdateRequestSchema(AsyncTestCase):
    """Test keylist update request schema."""

    async def test_make_model(self):
        keylist_update_request = KeylistUpdateRequest()
        keylist_update_request.updates.append(test_updates)
        data = keylist_update_request.serialize()
        model_instance = KeylistUpdateRequest.deserialize(data)
        assert type(model_instance) is type(keylist_update_request)