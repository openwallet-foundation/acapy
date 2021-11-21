import asyncio
import logging
import pytest

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from .....core.in_memory import InMemoryProfile
from .....core.protocol_registry import ProtocolRegistry
from .....core.goal_code_registry import GoalCodeRegistry
from .....storage.error import StorageNotFoundError
from .....messaging.responder import BaseResponder, MockResponder

from ....didcomm_prefix import DIDCommPrefix
from ....issue_credential.v1_0.controller import ISSUE_VC, PARTICIPATE_VC_INTERACTION
from ....issue_credential.v1_0.message_types import CONTROLLERS, MESSAGE_TYPES

from .. import manager as test_module
from ..manager import V20DiscoveryMgr, V20DiscoveryMgrError
from ..messages.queries import Queries, QueryItem
from ..messages.disclosures import Disclosures
from ..models.discovery_record import V20DiscoveryExchangeRecord

TEST_DISCOVERY_EX_REC = V20DiscoveryExchangeRecord(
    discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6"
)


class TestV20DiscoveryManager(AsyncTestCase):
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
        self.disclosures = Disclosures(
            disclosures=[
                {
                    "id": DIDCommPrefix.qualify_current("basicmessage/1.0/message"),
                    "feature-type": "protocol",
                    "roles": [],
                },
                {"feature-type": "goal-code", "id": "aries.sell.goods.consumer"},
            ]
        )
        self.queries = Queries(
            queries=[
                QueryItem(
                    feature_type="protocol", match="https://didcomm.org/tictactoe/1.*"
                ),
                QueryItem(feature_type="goal-code", match="aries.*"),
            ]
        )
        self.responder = MockResponder()
        self.profile.context.injector.bind_instance(BaseResponder, self.responder)
        self.manager = V20DiscoveryMgr(self.profile)
        assert self.manager.profile

    async def test_receive_disclosure(self):
        test_conn_id = "test123"
        self.queries.assign_thread_id("test123")
        with async_mock.patch.object(
            V20DiscoveryExchangeRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20DiscoveryExchangeRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_retrieve:
            mock_retrieve.return_value = TEST_DISCOVERY_EX_REC
            ex_rec = await self.manager.receive_disclose(
                disclose_msg=self.disclosures, connection_id=test_conn_id
            )
            save_ex.assert_called_once()
            assert ex_rec == V20DiscoveryExchangeRecord(
                discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
                disclosures=self.disclosures,
                connection_id=test_conn_id,
            )

    async def test_receive_disclosure_retreive_by_conn(self):
        test_conn_id = "test123"
        self.queries.assign_thread_id("test123")
        with async_mock.patch.object(
            V20DiscoveryExchangeRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20DiscoveryExchangeRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_exists_for_connection_id, async_mock.patch.object(
            V20DiscoveryExchangeRecord,
            "retrieve_by_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_by_connection_id, async_mock.patch.object(
            V20DiscoveryExchangeRecord, "retrieve_by_id", autospec=True
        ) as mock_retrieve_by_id:
            mock_retrieve_by_id.side_effect = StorageNotFoundError
            mock_exists_for_connection_id.return_value = True
            mock_retrieve_by_connection_id.return_value = TEST_DISCOVERY_EX_REC
            ex_rec = await self.manager.receive_disclose(
                disclose_msg=self.disclosures, connection_id=test_conn_id
            )
            save_ex.assert_called_once()
            assert ex_rec == V20DiscoveryExchangeRecord(
                discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
                disclosures=self.disclosures,
                connection_id=test_conn_id,
            )

    async def test_receive_disclosure_retreive_by_conn_not_found(self):
        test_conn_id = "test123"
        self.queries.assign_thread_id("test123")
        with async_mock.patch.object(
            V20DiscoveryExchangeRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20DiscoveryExchangeRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_exists_for_connection_id, async_mock.patch.object(
            V20DiscoveryExchangeRecord, "retrieve_by_id", autospec=True
        ) as mock_retrieve_by_id:
            mock_retrieve_by_id.side_effect = StorageNotFoundError
            mock_exists_for_connection_id.return_value = False
            ex_rec = await self.manager.receive_disclose(
                disclose_msg=self.disclosures, connection_id=test_conn_id
            )
            save_ex.assert_called_once()
            assert ex_rec == V20DiscoveryExchangeRecord(
                discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
                disclosures=self.disclosures,
                connection_id=test_conn_id,
            )

    async def test_receive_disclosure_retreive_new_ex_rec(self):
        test_conn_id = "test123"
        with async_mock.patch.object(
            V20DiscoveryExchangeRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20DiscoveryExchangeRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_exists_for_connection_id, async_mock.patch.object(
            V20DiscoveryExchangeRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_retrieve_by_id:
            mock_retrieve_by_id.side_effect = StorageNotFoundError
            mock_exists_for_connection_id.return_value = False
            ex_rec = await self.manager.receive_disclose(
                disclose_msg=self.disclosures, connection_id=test_conn_id
            )
            save_ex.assert_called_once()
            assert ex_rec == V20DiscoveryExchangeRecord(
                disclosures=self.disclosures,
                connection_id=test_conn_id,
            )

    async def test_proactive_disclosure(self):
        with async_mock.patch.object(
            V20DiscoveryMgr,
            "receive_query",
            async_mock.CoroutineMock(),
        ) as mock_receive_query, async_mock.patch.object(
            self.responder, "send", async_mock.CoroutineMock()
        ) as mock_send:
            mock_receive_query.return_value = Disclosures()
            await self.manager.proactive_disclose_features("test123")
            mock_send.assert_called_once()

    async def test_proactive_disclosure_no_responder(self):
        self.profile.context.injector.clear_binding(BaseResponder)
        with async_mock.patch.object(
            V20DiscoveryMgr,
            "receive_query",
            async_mock.CoroutineMock(),
        ) as mock_receive_query, async_mock.patch.object(
            self.responder, "send", async_mock.CoroutineMock()
        ) as mock_send:
            self._caplog.set_level(logging.WARNING)
            mock_receive_query.return_value = Disclosures()
            await self.manager.proactive_disclose_features("test123")
            assert (
                "Unable to send discover-features v2 disclosures" in self._caplog.text
            )

    async def test_check_if_disclosure_received(self):
        with async_mock.patch.object(
            V20DiscoveryExchangeRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_by_id:
            mock_retrieve_by_id.side_effect = [
                V20DiscoveryExchangeRecord(),
                V20DiscoveryExchangeRecord(disclosures=Disclosures()),
            ]
            assert await self.manager.check_if_disclosure_received(record_id="test123")

    async def test_create_and_send_query_x(self):
        with self.assertRaises(V20DiscoveryMgrError) as cm:
            await self.manager.create_and_send_query()
        assert "Atleast one protocol or goal-code" in str(cm.exception)

    async def test_create_and_send_query_with_connection(self):
        return_ex_rec = V20DiscoveryExchangeRecord(
            queries_msg=Queries(
                queries=[
                    QueryItem(feature_type="protocol", match="*"),
                    QueryItem(feature_type="goal-code", match="*"),
                ]
            )
        )
        with async_mock.patch.object(
            V20DiscoveryExchangeRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_exists_for_connection_id, async_mock.patch.object(
            V20DiscoveryExchangeRecord,
            "retrieve_by_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_by_connection_id, async_mock.patch.object(
            V20DiscoveryExchangeRecord,
            "save",
            async_mock.CoroutineMock(),
        ) as save_ex, async_mock.patch.object(
            V20DiscoveryMgr, "check_if_disclosure_received", async_mock.CoroutineMock()
        ) as mock_disclosure_received, async_mock.patch.object(
            self.responder, "send", async_mock.CoroutineMock()
        ) as mock_send:
            mock_exists_for_connection_id.return_value = True
            mock_retrieve_by_connection_id.return_value = V20DiscoveryExchangeRecord()
            mock_disclosure_received.return_value = return_ex_rec
            received_ex_rec = await self.manager.create_and_send_query(
                query_protocol="*", query_goal_code="*", connection_id="test123"
            )
            assert received_ex_rec.queries_msg == return_ex_rec.queries_msg
            mock_send.assert_called_once()

    async def test_create_and_send_query_with_connection_no_responder(self):
        self.profile.context.injector.clear_binding(BaseResponder)
        with async_mock.patch.object(
            V20DiscoveryExchangeRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(),
        ) as mock_exists_for_connection_id, async_mock.patch.object(
            V20DiscoveryExchangeRecord,
            "save",
            async_mock.CoroutineMock(),
        ) as save_ex, async_mock.patch.object(
            V20DiscoveryMgr, "check_if_disclosure_received", async_mock.CoroutineMock()
        ) as mock_disclosure_received:
            self._caplog.set_level(logging.WARNING)
            mock_exists_for_connection_id.return_value = False
            mock_disclosure_received.side_effect = asyncio.TimeoutError
            received_ex_rec = await self.manager.create_and_send_query(
                query_protocol="*", query_goal_code="*", connection_id="test123"
            )
            assert received_ex_rec.queries_msg.queries[0].match == "*"
            assert received_ex_rec.queries_msg.queries[0].feature_type in [
                "protocol",
                "goal-code",
            ]
            assert received_ex_rec.queries_msg.queries[1].match == "*"
            assert received_ex_rec.queries_msg.queries[0].feature_type in [
                "protocol",
                "goal-code",
            ]
            assert (
                "Unable to send discover-features v2 query message" in self._caplog.text
            )

    async def test_create_and_send_query_with_no_connection(self):
        with async_mock.patch.object(
            V20DiscoveryMgr,
            "receive_query",
            async_mock.CoroutineMock(),
        ) as mock_receive_query:
            mock_receive_query.return_value = Disclosures()
            received_ex_rec = await self.manager.create_and_send_query(
                query_protocol="*", query_goal_code="*"
            )
            assert received_ex_rec.queries_msg.queries[0].match == "*"
            assert received_ex_rec.queries_msg.queries[0].feature_type in [
                "protocol",
                "goal-code",
            ]
            assert received_ex_rec.queries_msg.queries[1].match == "*"
            assert received_ex_rec.queries_msg.queries[0].feature_type in [
                "protocol",
                "goal-code",
            ]
            assert received_ex_rec.disclosures.disclosures == []
