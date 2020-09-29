from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import BASIC_MESSAGE, PROTOCOL_PACKAGE

from ..basicmessage import BasicMessage


class TestBasicMessage(TestCase):
    def setUp(self):
        self.test_content = "hello"
        self.test_message = BasicMessage(content=self.test_content)

    def test_init(self):
        """Test initialization."""
        assert self.test_message.content == self.test_content
        assert self.test_message.sent_time

    def test_type(self):
        """Test type."""
        assert self.test_message._type == DIDCommPrefix.qualify_current(BASIC_MESSAGE)

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.basicmessage.BasicMessageSchema.load")
    def test_deserialize(self, mock_basic_message_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        msg = BasicMessage.deserialize(obj)
        mock_basic_message_schema_load.assert_called_once_with(obj)

        assert msg is mock_basic_message_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.basicmessage.BasicMessageSchema.dump")
    def test_serialize(self, mock_basic_message_schema_load):
        """
        Test serialization.
        """
        msg_dict = self.test_message.serialize()
        mock_basic_message_schema_load.assert_called_once_with(self.test_message)

        assert msg_dict is mock_basic_message_schema_load.return_value


class TestBasicMessageSchema(AsyncTestCase):
    """Test basic message schema."""

    async def test_make_model(self):
        basic_message = BasicMessage(content="hello")
        data = basic_message.serialize()
        model_instance = BasicMessage.deserialize(data)
        assert type(model_instance) is type(basic_message)
