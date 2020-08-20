from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase

from ..inner.keylist_update_result import KeylistUpdateResult
from ..keylist_update_response import KeylistUpdateResponse
from ...message_types import KEYLIST_UPDATE_RESPONSE, PROTOCOL_PACKAGE

test_recipient_key_data = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
test_action_data = "add"
test_result_data = "success"
test_updated = KeylistUpdateResult(recipient_key=test_recipient_key_data, action=test_action_data, result=test_result_data)

class TestKeylistUpdateResponse(TestCase):
    def setUp(self):
        self.test_message = KeylistUpdateResponse()
        self.test_message.updated.append(test_updated)

    def test_init(self):
        """Test initialization."""
        assert self.test_message.updated[0] == test_updated

    def test_type(self):
        """Test type."""
        assert self.test_message._type == KEYLIST_UPDATE_RESPONSE

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.keylist_update_response.KeylistUpdateResponseSchema.load")
    def test_deserialize(self, mock_keylist_update_response_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        msg = KeylistUpdateResponse.deserialize(obj)
        mock_keylist_update_response_schema_load.assert_called_once_with(obj)

        assert msg is mock_keylist_update_response_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.keylist_update_response.KeylistUpdateResponseSchema.dump")
    def test_serialize(self, mock_keylist_update_response_schema_load):
        """
        Test serialization.
        """
        msg_dict = self.test_message.serialize()
        mock_keylist_update_response_schema_load.assert_called_once_with(self.test_message)

        assert msg_dict is mock_keylist_update_response_schema_load.return_value


class TestKeylistUpdateResponseSchema(AsyncTestCase):
    """Test keylist update response schema."""

    async def test_make_model(self):
        keylist_update_response = KeylistUpdateResponse()
        keylist_update_response.updated.append(test_updated)
        data = keylist_update_response.serialize()
        model_instance = KeylistUpdateResponse.deserialize(data)
        assert type(model_instance) is type(keylist_update_response)