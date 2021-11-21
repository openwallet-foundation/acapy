import asyncio
import logging
import pytest

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from .....core.in_memory import InMemoryProfile
from .....storage.error import StorageNotFoundError
from .....messaging.responder import BaseResponder, MockResponder

from ....didcomm_prefix import DIDCommPrefix

from .. import manager as test_module
from ..manager import V10DiscoveryMgr
from ..messages.disclose import Disclose
from ..messages.query import Query
from ..models.discovery_record import V10DiscoveryExchangeRecord

TEST_DISCOVERY_EX_REC = V10DiscoveryExchangeRecord(
    discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6"
)


class TestV10DiscoveryManager(AsyncTestCase):
    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

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
        self.responder = MockResponder()
        self.profile.context.injector.bind_instance(BaseResponder, self.responder)
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

    async def test_check_if_disclosure_received(self):
        with async_mock.patch.object(
            V10DiscoveryExchangeRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_by_id:
            mock_retrieve_by_id.side_effect = [
                V10DiscoveryExchangeRecord(),
                V10DiscoveryExchangeRecord(disclose=Disclose()),
            ]
            assert await self.manager.check_if_disclosure_received(record_id="test123")

    async def test_create_and_send_query_with_connection(self):
        return_ex_rec = V10DiscoveryExchangeRecord(query_msg=Query(query="*"))
        with async_mock.patch.object(
            V10DiscoveryExchangeRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_exists_for_connection_id, async_mock.patch.object(
            V10DiscoveryExchangeRecord,
            "retrieve_by_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_by_connection_id, async_mock.patch.object(
            V10DiscoveryExchangeRecord,
            "save",
            async_mock.CoroutineMock(),
        ) as save_ex, async_mock.patch.object(
            V10DiscoveryMgr, "check_if_disclosure_received", async_mock.CoroutineMock()
        ) as mock_disclosure_received, async_mock.patch.object(
            self.responder, "send", async_mock.CoroutineMock()
        ) as mock_send:
            mock_exists_for_connection_id.return_value = True
            mock_retrieve_by_connection_id.return_value = V10DiscoveryExchangeRecord()
            mock_disclosure_received.return_value = return_ex_rec
            received_ex_rec = await self.manager.create_and_send_query(
                query="*", connection_id="test123"
            )
            assert received_ex_rec.query_msg == return_ex_rec.query_msg
            mock_send.assert_called_once()

    async def test_create_and_send_query_with_connection_no_responder(self):
        self.profile.context.injector.clear_binding(BaseResponder)
        with async_mock.patch.object(
            V10DiscoveryExchangeRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_exists_for_connection_id, async_mock.patch.object(
            V10DiscoveryExchangeRecord,
            "save",
            async_mock.CoroutineMock(),
        ) as save_ex, async_mock.patch.object(
            V10DiscoveryMgr, "check_if_disclosure_received", async_mock.CoroutineMock()
        ) as mock_disclosure_received:
            self._caplog.set_level(logging.WARNING)
            mock_exists_for_connection_id.return_value = False
            mock_disclosure_received.side_effect = asyncio.TimeoutError
            received_ex_rec = await self.manager.create_and_send_query(
                query="*", connection_id="test123"
            )
            assert received_ex_rec.query_msg.query == "*"
            assert "Unable to send discover-features v1" in self._caplog.text

    async def test_create_and_send_query_with_no_connection(self):
        with async_mock.patch.object(
            V10DiscoveryMgr,
            "receive_query",
            async_mock.CoroutineMock(),
        ) as mock_receive_query:
            mock_receive_query.return_value = Disclose()
            received_ex_rec = await self.manager.create_and_send_query(query="*")
            assert received_ex_rec.query_msg.query == "*"
            assert received_ex_rec.disclose.protocols == []
