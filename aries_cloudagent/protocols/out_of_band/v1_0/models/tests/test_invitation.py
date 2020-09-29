import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ..invitation import InvitationRecord, InvitationRecordSchema


class TestInvitationRecord(AsyncTestCase):
    def test_invitation_record(self):
        """Test invitation record."""
        invi = InvitationRecord(invitation_id="0")
        assert isinstance(invi, InvitationRecord)
        assert invi.invitation_id == "0"
        assert invi.record_value == {
            "invitation_id": "0",
            "invitation": None,
            "state": None,
            "trace": False,
        }

        another = InvitationRecord(invitation_id="1")
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
