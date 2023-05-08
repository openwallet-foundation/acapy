import json

from unittest import mock, TestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import FORWARD, PROTOCOL_PACKAGE
from ..forward import Forward, ForwardSchema


class TestForward(TestCase):
    to = "to"
    msg = {"msg": "body"}

    def setUp(self):
        self.message = Forward(to=self.to, msg=self.msg)

    def test_init(self):
        assert self.message.to == self.to

    def test_type(self):
        assert self.message._type == DIDCommPrefix.qualify_current(FORWARD)

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
        message = Forward(to="to", msg={"some": "msg"})
        data = message.serialize()
        model_instance = Forward.deserialize(data)
        assert isinstance(model_instance, Forward)

    def test_make_model_str(self):
        MSG = {"some": "msg"}
        message = Forward(to="to", msg=json.dumps(MSG))
        data = message.serialize()
        model_instance = Forward.deserialize(data)
        assert isinstance(model_instance, Forward)

        assert {"msg": MSG} == ForwardSchema().handle_str_message(
            data={"msg": json.dumps(MSG)}
        )
