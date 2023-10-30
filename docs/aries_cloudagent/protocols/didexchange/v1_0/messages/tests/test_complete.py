from unittest import TestCase

from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import DIDX_COMPLETE
from ..complete import DIDXComplete

THID = "dummy-thid"
PTHID = "dummy-pthid"


class TestDIDXComplete(TestCase):
    def test_init_type(self):
        complete = DIDXComplete()
        assert complete._type == DIDCommPrefix.qualify_current(DIDX_COMPLETE)

    def test_serde(self):
        obj = {"~thread": {"thid": THID, "pthid": PTHID}}
        complete = DIDXComplete.deserialize(obj)
        assert complete._type == DIDCommPrefix.qualify_current(DIDX_COMPLETE)

        complete_dict = complete.serialize()
        assert complete_dict["~thread"] == obj["~thread"]


class TestDIDXCompleteSchema(TestCase):
    def test_make_model(self):
        complete = DIDXComplete()
        complete.assign_thread_id(THID, PTHID)
        data = complete.serialize()
        model_instance = DIDXComplete.deserialize(data)
        assert isinstance(model_instance, DIDXComplete)

    def test_serde_x(self):
        DIDXComplete.deserialize({})  # no thread attachment: OK as model
        x_complete = DIDXComplete()  # no thread attachment: should not deserialize
        with self.assertRaises(BaseModelError):
            data = x_complete.serialize()
