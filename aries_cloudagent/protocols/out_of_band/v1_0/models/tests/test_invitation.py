import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ......core.in_memory import InMemoryProfile

from ..invitation import InvitationRecord, InvitationRecordSchema


class TestInvitationRecord(AsyncTestCase):
    def test_invitation_record(self):
        """Test invitation record."""
        invi_rec = InvitationRecord(invi_msg_id="12345")
        assert isinstance(invi_rec, InvitationRecord)
        assert invi_rec.record_value == {
            "invitation": None,
            "invitation_url": None,
            "state": None,
            "trace": False,
            "auto_accept": False,
            "multi_use": False,
        }

        another = InvitationRecord(invi_msg_id="99999")
        assert invi_rec != another

    async def test_retrieve_by_public_did(self):
        """Test retrieve by public DID."""
        TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
        session = InMemoryProfile.test_session()
        invi_rec = InvitationRecord(invi_msg_id="12345", public_did=TEST_DID)
        await invi_rec.save(session)
        result = await InvitationRecord.retrieve_by_public_did(
            session=session, public_did=TEST_DID
        )
        assert result == invi_rec


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
