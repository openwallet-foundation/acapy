from ..forward import Forward
from ....message_types import MessageTypes

from unittest import mock, TestCase


class TestForward(TestCase):

    to = ["to"]
    msg = "msg"

    def setUp(self):
        self.forward = Forward(to=self.to, msg=self.msg)

    def test_init(self):
        assert self.forward.to == self.to

    def test_type(self):
        assert self.forward._type == MessageTypes.FORWARD.value

    @mock.patch(
        "indy_catalyst_agent.messaging.routing.messages.forward.ForwardSchema.load"
    )
    def test_deserialize(self, forward_schema_load):
        obj = {"obj": "obj"}

        forward = Forward.deserialize(obj)
        forward_schema_load.assert_called_once_with(obj)

        assert forward is forward_schema_load.return_value

    @mock.patch(
        "indy_catalyst_agent.messaging.routing.messages.forward.ForwardSchema.dump"
    )
    def test_serialize(self, forward_schema_dump):
        forward_dict = self.forward.serialize()
        forward_schema_dump.assert_called_once_with(self.forward)

        assert forward_dict is forward_schema_dump.return_value


class TestForwardSchema(TestCase):

    def test_make_model(self):
        forward = Forward(to="to", msg="msg")
        data = forward.serialize()
        model_instance = Forward.deserialize(data)
        assert isinstance(model_instance, Forward)
