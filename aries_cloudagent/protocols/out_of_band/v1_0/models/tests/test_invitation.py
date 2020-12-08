import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ..invitation import InvitationRecord, InvitationRecordSchema


class TestInvitationRecord(AsyncTestCase):
    def test_invitation_record(self):
        """Test invitation record."""
        invi = InvitationRecord(invi_msg_id="12345")
        assert isinstance(invi, InvitationRecord)
        assert invi.record_value == {
            "invitation": None,
            "invitation_url": None,
            "state": None,
            "trace": False,
            "auto_accept": False,
            "multi_use": False,
        }

        another = InvitationRecord(invi_msg_id="99999")
        assert invi != another


class TestInvitationRecordSchema(AsyncTestCase):
    def test_make_record(self):
        """Test making record."""
        data = {
            "invitation_id": "0",
            "state": InvitationRecord.STATE_AWAIT_RESPONSE,
            "invitation": {"sample": "value"},
        }
        model_instance = InvitationRecord.deserialize(data)
        assert isinstance(model_instance, InvitationRecord)
