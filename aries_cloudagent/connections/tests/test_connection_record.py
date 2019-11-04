from asynctest import TestCase as AsyncTestCase

from ...config.injection_context import InjectionContext
from ...storage.base import BaseStorage
from ...storage.basic import BasicStorage

from ..models.connection_record import ConnectionRecord


class TestConfig:

    test_seed = "testseed000000000000000000000001"
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_endpoint = "http://localhost"

    test_target_did = "GbuDUYXaUZRfHD2jeDuQuP"
    test_target_verkey = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"


class TestConnectionRecord(AsyncTestCase, TestConfig):
    def setUp(self):
        self.storage = BasicStorage()
        self.context = InjectionContext()
        self.context.injector.bind_instance(BaseStorage, self.storage)
        self.test_info = ConnectionRecord(
            my_did=self.test_did,
            their_did=self.test_target_did,
            their_role=None,
            state=ConnectionRecord.STATE_ACTIVE,
        )

    async def test_save_retrieve_compare(self):
        record = ConnectionRecord(my_did=self.test_did)
        record_id = await record.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_id(self.context, record_id)
        assert fetched and fetched == record

        bad_record = ConnectionRecord(my_did=None)
        assert bad_record != record

    async def test_active_is_ready(self):
        record = ConnectionRecord(
            my_did=self.test_did, state=ConnectionRecord.STATE_ACTIVE
        )
        record_id = await record.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_id(self.context, record_id)

        assert fetched.is_ready == True

    async def test_response_is_ready(self):
        record = ConnectionRecord(
            my_did=self.test_did, state=ConnectionRecord.STATE_RESPONSE
        )
        record_id = await record.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_id(self.context, record_id)

        assert fetched.is_ready is True

    async def test_request_is_not_ready(self):
        record = ConnectionRecord(
            my_did=self.test_did, state=ConnectionRecord.STATE_REQUEST
        )
        record_id = await record.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_id(self.context, record_id)

        assert fetched.is_ready is False

    async def test_invitation_is_not_multi_use(self):
        record = ConnectionRecord(
            my_did=self.test_did,
            state=ConnectionRecord.STATE_INVITATION,
            invitation_mode=ConnectionRecord.INVITATION_MODE_ONCE,
        )
        record_id = await record.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_id(self.context, record_id)

        assert fetched.is_multiuse_invitation is False

    async def test_invitation_is_multi_use(self):
        record = ConnectionRecord(
            my_did=self.test_did,
            state=ConnectionRecord.STATE_INVITATION,
            invitation_mode=ConnectionRecord.INVITATION_MODE_MULTI,
        )
        record_id = await record.save(self.context)
        fetched = await ConnectionRecord.retrieve_by_id(self.context, record_id)

        assert fetched.is_multiuse_invitation is True
