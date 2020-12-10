"""Helper classes and functions for message tests."""

from unittest import mock

from ......messaging.agent_message import AgentMessage, AgentMessageSchema
from .....didcomm_prefix import DIDCommPrefix


class MessageTest:
    """Base class for message tests."""

    TYPE: str = None
    CLASS = AgentMessage
    SCHEMA = AgentMessageSchema
    VALUES: dict = {}

    def setUp(self):
        self.message = self.CLASS(**self.VALUES)

    def test_init(self):
        """Test initialization of message."""
        for key, value in self.VALUES.items():
            assert hasattr(self.message, key) and getattr(self.message, key) == value

    def test_type(self):
        """Test type matches expected."""
        assert self.message._type == DIDCommPrefix.qualify_current(self.TYPE)

    def test_deserialize(self):
        """Test deserialization of message."""
        with mock.patch.object(self.SCHEMA, "load") as message_schema_load:
            obj = {"obj": "obj"}

            message = self.CLASS.deserialize(obj)
            message_schema_load.assert_called_once_with(obj)

            assert message is message_schema_load.return_value

    def test_serialize(self):
        """Test serialization of message."""
        with mock.patch.object(self.SCHEMA, "dump") as message_schema_dump:
            message_dict = self.message.serialize()
            message_schema_dump.assert_called_once_with(self.message)

            assert message_dict is message_schema_dump.return_value

    def test_make_model(self):
        """Test serialize then deserialize results in instance of model."""
        message = self.CLASS(**self.VALUES)
        data = message.serialize()
        model_instance = self.CLASS.deserialize(data)
        assert isinstance(model_instance, self.CLASS)
