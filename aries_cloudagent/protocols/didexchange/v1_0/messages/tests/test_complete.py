from unittest import mock, TestCase

from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CONN23_COMPLETE
from ..complete import Conn23Complete

THID = "dummy-thid"
PTHID = "dummy-pthid"


class TestConn23Complete(TestCase):
    def test_init_type(self):
        complete = Conn23Complete()
        assert complete._type == DIDCommPrefix.qualify_current(CONN23_COMPLETE)

    def test_serde(self, mock_invitation_schema_load):
        obj = {"~thread": {"thid": THID, "pthid": PTHID}}
        complete = Conn23Complete.deserialize(obj)
        assert complete._type == DIDCommPrefix.qualify_current(CONN23_COMPLETE)

        complete_dict = complete.serialize()
        assert complete_dict["~thread"] == obj


class TestConn23CompleteSchema(TestCase):
    def test_make_model(self):
        complete = Conn23Complete().assign_thread_id(THID, PTHID)
        data = complete.serialize()
        model_instance = Conn23Complete.deserialize(data)
        assert isinstance(model_instance, Conn23Complete)

    def test_make_model_x(self):
        x_complete = Conn23Complete()  # no thread attachment
        data = x_complete.serialize()
        with self.assertRaises(BaseModelError):
            Conn23Complete.deserialize(data)
