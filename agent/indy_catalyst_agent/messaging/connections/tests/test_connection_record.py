from asynctest import TestCase as AsyncTestCase

from ..models.connection_record import ConnectionRecord
from ....storage.basic import BasicStorage


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
        self.test_info = ConnectionRecord(
            my_did=self.test_did,
            their_did=self.test_target_did,
            their_role=None,
            state=ConnectionRecord.STATE_ACTIVE,
        )

    async def test_save_retrieve_compare(self):
        record = ConnectionRecord(my_did=self.test_did)
        record_id = await record.save(self.storage)
        fetched = await ConnectionRecord.retrieve_by_id(self.storage, record_id)
        assert fetched and fetched == record

        bad_record = ConnectionRecord(my_did=None)
        assert bad_record != record
