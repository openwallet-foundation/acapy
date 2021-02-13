import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ..invitation import InvitationRecord, InvitationRecordSchema


class TestInvitationRecord(AsyncTestCase):
    def test_invitation_record(self):
        """Test invitation record."""
        invi_rec = InvitationRecord(invi_msg_id="12345")
        assert invi_rec.invitation_id is None  # not saved
        assert isinstance(invi_rec, InvitationRecord)
        assert invi_rec.record_value == {
            "invitation": None,
            "invitation_url": None,
            "state": None,
            "trace": False,
        }

        another = InvitationRecord(invi_msg_id="99999")
        assert invi_rec != another


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
