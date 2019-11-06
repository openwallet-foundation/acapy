from ..forward import Forward
from ...message_types import FORWARD, PROTOCOL_PACKAGE

from unittest import mock, TestCase


class TestForward(TestCase):

    to = "to"
    msg = "msg"

    def setUp(self):
        self.message = Forward(to=self.to, msg=self.msg)

    def test_init(self):
        assert self.message.to == self.to

    def test_type(self):
        assert self.message._type == FORWARD

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.forward.ForwardSchema.load")
    def test_deserialize(self, message_schema_load):
        obj = {"obj": "obj"}

        message = Forward.deserialize(obj)
        message_schema_load.assert_called_once_with(obj)

        assert message is message_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.forward.ForwardSchema.dump")
    def test_serialize(self, message_schema_dump):
        message_dict = self.message.serialize()
        message_schema_dump.assert_called_once_with(self.message)

        assert message_dict is message_schema_dump.return_value


class TestForwardSchema(TestCase):
    def test_make_model(self):
        message = Forward(to="to", msg="msg")
        data = message.serialize()
        model_instance = Forward.deserialize(data)
        assert isinstance(model_instance, Forward)
