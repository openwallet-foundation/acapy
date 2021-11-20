from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ......core.in_memory import InMemoryProfile
from ......storage.error import StorageDuplicateError, StorageNotFoundError

from .....didcomm_prefix import DIDCommPrefix

from ...messages.query import Query
from ...messages.disclose import Disclose

from ..discovery_record import V10DiscoveryExchangeRecord


class TestV10DiscoveryExchangeRecord(AsyncTestCase):
    """Test de/serialization."""

    async def test_record(self):
        same = [
            V10DiscoveryExchangeRecord(
                query_msg=Query(query="*"), connection_id="test123"
            )
        ] * 2
        diff = [
            V10DiscoveryExchangeRecord(
                query_msg=Query(query="test1.*"), connection_id="test123"
            ),
            V10DiscoveryExchangeRecord(
                query_msg=Query(query="test2.*"), connection_id="test123"
            ),
            V10DiscoveryExchangeRecord(
                query_msg=Query(query="test3.*"), connection_id="test123"
            ),
        ]

        for i in range(len(same) - 1):
            for j in range(i, len(same)):
                assert same[i] == same[j]

        for i in range(len(diff) - 1):
            for j in range(i, len(diff)):
                assert diff[i] == diff[j] if i == j else diff[i] != diff[j]

    async def test_serde(self):
        """Test de/serialization."""
        test_protocols = [
            {
                "pid": DIDCommPrefix.qualify_current("basicmessage/1.0/message"),
                "roles": [],
            }
        ]
        query_msg = Query(query="*", comment="test")
        disclose_msg = Disclose(protocols=test_protocols)
        ex_rec = V10DiscoveryExchangeRecord(
            disclose=disclose_msg,
        )
        ex_rec.query_msg = query_msg
        assert type(ex_rec.query_msg) == Query
        ser = ex_rec.serialize()
        deser = V10DiscoveryExchangeRecord.deserialize(ser)
        assert type(deser.query_msg) == Query

        assert type(ex_rec.disclose) == Disclose
        ser = ex_rec.serialize()
        deser = V10DiscoveryExchangeRecord.deserialize(ser)
        assert type(deser.disclose) == Disclose

    async def test_retrieve_by_conn_id(self):
        session = InMemoryProfile.test_session()
        record = V10DiscoveryExchangeRecord(
            query_msg=Query(query="*"), connection_id="test123"
        )
        await record.save(session)
        retrieved = await V10DiscoveryExchangeRecord.retrieve_by_connection_id(
            session=session, connection_id="test123"
        )
        assert retrieved
        assert retrieved.connection_id == "test123"

    async def test_exists_for_connection_id(self):
        session = InMemoryProfile.test_session()
        record = V10DiscoveryExchangeRecord(
            query_msg=Query(query="*"), connection_id="test123"
        )
        await record.save(session)
        check = await V10DiscoveryExchangeRecord.exists_for_connection_id(
            session=session, connection_id="test123"
        )
        assert check

    async def test_exists_for_connection_id_not_found(self):
        session = InMemoryProfile.test_session()
        with async_mock.patch.object(
            V10DiscoveryExchangeRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_by_tag_filter:
            mock_retrieve_by_tag_filter.side_effect = StorageNotFoundError
            check = await V10DiscoveryExchangeRecord.exists_for_connection_id(
                session=session, connection_id="test123"
            )
            assert not check

    async def test_exists_for_connection_id_duplicate(self):
        session = InMemoryProfile.test_session()
        with async_mock.patch.object(
            V10DiscoveryExchangeRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_by_tag_filter:
            mock_retrieve_by_tag_filter.side_effect = StorageDuplicateError
            check = await V10DiscoveryExchangeRecord.exists_for_connection_id(
                session=session, connection_id="test123"
            )
            assert check
