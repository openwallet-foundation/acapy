from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from ..keylist_update_result import KeylistUpdateResult
from ....message_types import PROTOCOL_PACKAGE


test_recipient_key_data = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
test_action_data = "add"
test_result_data = "success"

class TestKeylistUpdateResult(TestCase):
    def setUp(self):
        self.test_recipient_key = test_recipient_key_data
        self.test_action = test_action_data
        self.test_result = test_result_data
        self.test_message = KeylistUpdateResult(recipient_key=self.test_recipient_key, action=self.test_action, result=self.test_result)

    def test_init(self):
        """Test initialization."""
        assert self.test_message.recipient_key == self.test_recipient_key
        assert self.test_message.action == self.test_action
        assert self.test_message.result == self.test_result

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.inner.keylist_update_result.KeylistUpdateResultSchema.load")
    def test_deserialize(self, mock_keylist_update_result_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        msg = KeylistUpdateResult.deserialize(obj)
        mock_keylist_update_result_schema_load.assert_called_once_with(obj)

        assert msg is mock_keylist_update_result_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.inner.keylist_update_result.KeylistUpdateResultSchema.dump")
    def test_serialize(self, mock_keylist_update_result_schema_load):
        """
        Test serialization.
        """
        msg_dict = self.test_message.serialize()
        mock_keylist_update_result_schema_load.assert_called_once_with(self.test_message)

        assert msg_dict is mock_keylist_update_result_schema_load.return_value


class TestKeylistUpdateResultSchema(AsyncTestCase):
    """Test keylist update result schema."""

    async def test_make_model(self):
        keylist_update_result = KeylistUpdateResult(recipient_key=test_recipient_key_data, action=test_action_data, result=test_result_data)
        data = keylist_update_result.serialize()
        model_instance = KeylistUpdateResult.deserialize(data)
        assert type(model_instance) is type(keylist_update_result)