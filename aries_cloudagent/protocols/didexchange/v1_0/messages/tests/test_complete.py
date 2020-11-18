from unittest import mock, TestCase

from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CONN_COMPLETE
from ..complete import ConnComplete

THID = "dummy-thid"
PTHID = "dummy-pthid"


class TestConnComplete(TestCase):
    def test_init_type(self):
        complete = ConnComplete()
        assert complete._type == DIDCommPrefix.qualify_current(CONN_COMPLETE)

    def test_serde(self):
        obj = {"~thread": {"thid": THID, "pthid": PTHID}}
        complete = ConnComplete.deserialize(obj)
        assert complete._type == DIDCommPrefix.qualify_current(CONN_COMPLETE)

        complete_dict = complete.serialize()
        assert complete_dict["~thread"] == obj["~thread"]


class TestConnCompleteSchema(TestCase):
    def test_make_model(self):
        complete = ConnComplete()
        complete.assign_thread_id(THID, PTHID)
        data = complete.serialize()
        model_instance = ConnComplete.deserialize(data)
        assert isinstance(model_instance, ConnComplete)

    def test_serde_x(self):
        ConnComplete.deserialize({})  # no thread attachment: OK as model
        x_complete = ConnComplete()  # no thread attachment: should not deserialize
        with self.assertRaises(BaseModelError):
            data = x_complete.serialize()
