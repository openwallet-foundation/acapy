from asynctest import mock as async_mock, TestCase as AsyncTestCase

from .....core.in_memory import InMemoryProfile
from .....core.protocol_registry import ProtocolRegistry
from .....core.goal_code_registry import GoalCodeRegistry
from .....storage.error import StorageNotFoundError

from ....didcomm_prefix import DIDCommPrefix
from ....issue_credential.v1_0.controller import ISSUE_VC, PARTICIPATE_VC_INTERACTION
from ....issue_credential.v1_0.message_types import CONTROLLERS, MESSAGE_TYPES

from ..manager import V20DiscoveryMgr
from ..messages.queries import Queries, QueryItem
from ..messages.disclosures import Disclosures
from ..models.discovery_record import V20DiscoveryExchangeRecord

TEST_DISCOVERY_EX_REC = V20DiscoveryExchangeRecord(
    discovery_exchange_id="3fa85f64-5717-4562-b3fc-2c963f66afa6"
)


class TestV20DiscoveryManager(AsyncTestCase):
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
