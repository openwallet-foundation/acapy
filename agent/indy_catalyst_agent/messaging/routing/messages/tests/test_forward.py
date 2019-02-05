from ..forward import Forward, ForwardSchema
from ....message_types import MessageTypes

from unittest import mock, TestCase


class TestForward(TestCase):
    to = "to"
    msg = "msg"

    def test_init(self):
        forward = Forward(self.to, self.msg)
        assert forward.to == self.to

    def test_type(self):
        forward = Forward(self.to, self.msg)

        assert forward._type == MessageTypes.FORWARD.value

    @mock.patch("indy_catalyst_agent.messaging.routing.messages.forward.ForwardSchema.load")
    def test_deserialize(self, forward_schema_load):
        obj = {"obj": "obj"}

        forward = Forward.deserialize(obj)
        forward_schema_load.assert_called_once_with(obj)

        assert forward is forward_schema_load.return_value

    @mock.patch("indy_catalyst_agent.messaging.routing.messages.forward.ForwardSchema.dump")
    def test_serialize(self, forward_schema_dump):
        forward = Forward(self.to, self.msg)

        forward_dict = forward.serialize()
        forward_schema_dump.assert_called_once_with(forward)

        assert forward_dict is forward_schema_dump.return_value


class TestForwardSchema(TestCase):
    forward = Forward("to", "msg")

    def test_make_model(self):
        data = self.forward.serialize()
        model_instance = Forward.deserialize(data)
        assert type(model_instance) is type(self.forward)
