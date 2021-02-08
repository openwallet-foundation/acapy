import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ......cache.base import BaseCache
from ......cache.in_memory import InMemoryCache
from ......core.in_memory import InMemoryProfile
from ......ledger.base import BaseLedger

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

    async def test_retrieve_by_public_did(self):
        """Test retrieval by public DID."""
        test_did = "55GkHamhTU1ZbTbV2ab9DE"
        test_endpoint = "http://localhost"

        session = InMemoryProfile.test_session()
        ledger = async_mock.create_autospec(BaseLedger)
        ledger.__aenter__ = async_mock.CoroutineMock(return_value=ledger)
        ledger.get_endpoint_for_did = async_mock.CoroutineMock(
            return_value=test_endpoint
        )
        session.context.injector.bind_instance(BaseLedger, ledger)

        cache = InMemoryCache()
        session.context.injector.bind_instance(BaseCache, cache)

        invi_rec = await InvitationRecord.create_and_save_public(
            session=session,
            public_did=test_did,
        )
        invi_rec_0 = await InvitationRecord.retrieve_by_public_did(
            session,  # put it in the cache
            test_did,
        )
        invi_rec_1 = await InvitationRecord.retrieve_by_public_did(
            session, test_did  # get it out of the cache
        )

        assert invi_rec == invi_rec_0 and invi_rec_0 == invi_rec_1


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
