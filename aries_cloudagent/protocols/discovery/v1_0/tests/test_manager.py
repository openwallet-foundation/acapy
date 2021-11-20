from asynctest import mock as async_mock, TestCase as AsyncTestCase

from .....core.in_memory import InMemoryProfile
from .....core.protocol_registry import ProtocolRegistry
from .....storage.error import StorageNotFoundError

from ....didcomm_prefix import DIDCommPrefix

from ..manager import V10DiscoveryMgr
from ..messages.disclose import Disclose
from ..messages.query import Query
from ..models.discovery_record import V10DiscoveryExchangeRecord

TEST_DISCOVERY_EX_REC = V10DiscoveryExchangeRecord(
    discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6"
)


class TestV10DiscoveryManager(AsyncTestCase):
    async def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.profile = self.session.profile
        self.context = self.profile.context
        setattr(
            self.profile, "session", async_mock.MagicMock(return_value=self.session)
        )
        self.manager = V10DiscoveryMgr(self.profile)
        self.disclose = Disclose(
            protocols=[
                {
                    "pid": DIDCommPrefix.qualify_current(
                        "test_proto/v1.0/test_message"
                    ),
                    "roles": [],
                }
            ]
        )
        self.query = Query(query="*")
        self.query.assign_thread_id("test123")
        assert self.manager.profile

    async def test_receive_disclosure(self):
        test_conn_id = "test123"
        self.disclose.assign_thread_id("test123")
        with async_mock.patch.object(
            V10DiscoveryExchangeRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10DiscoveryExchangeRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_retrieve:
            mock_retrieve.return_value = TEST_DISCOVERY_EX_REC
            ex_rec = await self.manager.receive_disclose(
                disclose_msg=self.disclose, connection_id=test_conn_id
            )
            save_ex.assert_called_once()
            assert ex_rec == V10DiscoveryExchangeRecord(
                discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
                disclose=self.disclose,
                connection_id=test_conn_id,
            )

    async def test_receive_disclosure_retreive_by_conn(self):
        test_conn_id = "test123"
        self.disclose.assign_thread_id("test123")
        with async_mock.patch.object(
            V10DiscoveryExchangeRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10DiscoveryExchangeRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_exists_for_connection_id, async_mock.patch.object(
            V10DiscoveryExchangeRecord,
            "retrieve_by_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_by_connection_id, async_mock.patch.object(
            V10DiscoveryExchangeRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_retrieve_by_id:
            mock_retrieve_by_id.side_effect = StorageNotFoundError
            mock_exists_for_connection_id.return_value = True
            mock_retrieve_by_connection_id.return_value = TEST_DISCOVERY_EX_REC
            ex_rec = await self.manager.receive_disclose(
                disclose_msg=self.disclose, connection_id=test_conn_id
            )
            save_ex.assert_called_once()
            assert ex_rec == V10DiscoveryExchangeRecord(
                discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
                disclose=self.disclose,
                connection_id=test_conn_id,
            )

    async def test_receive_disclosure_retreive_by_conn_not_found(self):
        test_conn_id = "test123"
        self.disclose.assign_thread_id("test123")
        with async_mock.patch.object(
            V10DiscoveryExchangeRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10DiscoveryExchangeRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_exists_for_connection_id, async_mock.patch.object(
            V10DiscoveryExchangeRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_retrieve_by_id:
            mock_retrieve_by_id.side_effect = StorageNotFoundError
            mock_exists_for_connection_id.return_value = False
            ex_rec = await self.manager.receive_disclose(
                disclose_msg=self.disclose, connection_id=test_conn_id
            )
            save_ex.assert_called_once()
            assert ex_rec == V10DiscoveryExchangeRecord(
                discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
                disclose=self.disclose,
                connection_id=test_conn_id,
            )

    async def test_receive_disclosure_retreive_new_ex_rec(self):
        test_conn_id = "test123"
        with async_mock.patch.object(
            V10DiscoveryExchangeRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10DiscoveryExchangeRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_exists_for_connection_id, async_mock.patch.object(
            V10DiscoveryExchangeRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_retrieve_by_id:
            mock_retrieve_by_id.side_effect = StorageNotFoundError
            mock_exists_for_connection_id.return_value = False
            ex_rec = await self.manager.receive_disclose(
                disclose_msg=self.disclose, connection_id=test_conn_id
            )
            save_ex.assert_called_once()
            assert ex_rec == V10DiscoveryExchangeRecord(
                disclose=self.disclose,
                connection_id=test_conn_id,
            )
