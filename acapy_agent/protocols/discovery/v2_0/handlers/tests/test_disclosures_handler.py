import pytest
import pytest_asyncio

from ......core.protocol_registry import ProtocolRegistry
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......storage.error import StorageNotFoundError
from ......tests import mock
from ......utils.testing import create_test_profile
from .....didcomm_prefix import DIDCommPrefix
from ...handlers.disclosures_handler import DisclosuresHandler
from ...messages.disclosures import Disclosures
from ...messages.queries import Queries, QueryItem
from ...models.discovery_record import V20DiscoveryExchangeRecord

TEST_MESSAGE_FAMILY = "doc/proto/1.0"
TEST_MESSAGE_TYPE = TEST_MESSAGE_FAMILY + "/message"


@pytest_asyncio.fixture
async def request_context():
    ctx = RequestContext.test_context(await create_test_profile())
    ctx.connection_ready = True
    ctx.connection_record = mock.MagicMock(connection_id="test123")
    yield ctx


class TestDisclosuresHandler:
    @pytest.mark.asyncio
    async def test_disclosures(self, request_context):
        registry = ProtocolRegistry()
        registry.register_message_types({TEST_MESSAGE_TYPE: object()})
        request_context.injector.bind_instance(ProtocolRegistry, registry)
        disclosures = Disclosures(
            disclosures=[
                {
                    "id": DIDCommPrefix.qualify_current("basicmessage/1.0/message"),
                    "feature-type": "protocol",
                    "roles": [],
                },
                {"feature-type": "goal-code", "id": "aries.sell.goods.consumer"},
            ]
        )
        test_queries = [
            QueryItem(feature_type="protocol", match="https://didcomm.org/tictactoe/1.*"),
            QueryItem(feature_type="goal-code", match="aries.*"),
        ]
        queries = Queries(queries=test_queries)
        discovery_record = V20DiscoveryExchangeRecord(
            connection_id="test123",
            thread_id="test123",
            queries_msg=queries,
        )
        disclosures.assign_thread_id("test123")
        request_context.message = disclosures

        handler = DisclosuresHandler()
        mock_responder = MockResponder()
        with mock.patch.object(
            V20DiscoveryExchangeRecord,
            "retrieve_by_id",
            mock.CoroutineMock(return_value=discovery_record),
        ):
            await handler.handle(request_context, mock_responder)
            assert not mock_responder.messages

    @pytest.mark.asyncio
    async def test_disclosures_connection_id_no_thid(self, request_context):
        registry = ProtocolRegistry()
        registry.register_message_types({TEST_MESSAGE_TYPE: object()})
        request_context.injector.bind_instance(ProtocolRegistry, registry)
        disclosures = Disclosures(
            disclosures=[
                {
                    "id": DIDCommPrefix.qualify_current("basicmessage/1.0/message"),
                    "feature-type": "protocol",
                    "roles": [],
                },
                {"feature-type": "goal-code", "id": "aries.sell.goods.consumer"},
            ]
        )
        test_queries = [
            QueryItem(feature_type="protocol", match="https://didcomm.org/tictactoe/1.*"),
            QueryItem(feature_type="goal-code", match="aries.*"),
        ]
        queries = Queries(queries=test_queries)
        discovery_record = V20DiscoveryExchangeRecord(
            connection_id="test123",
            thread_id="test123",
            queries_msg=queries,
        )
        disclosures.assign_thread_id("test123")
        request_context.message = disclosures

        handler = DisclosuresHandler()
        mock_responder = MockResponder()
        with (
            mock.patch.object(
                V20DiscoveryExchangeRecord,
                "retrieve_by_id",
                mock.CoroutineMock(side_effect=StorageNotFoundError),
            ),
            mock.patch.object(
                V20DiscoveryExchangeRecord,
                "retrieve_by_connection_id",
                mock.CoroutineMock(return_value=discovery_record),
            ),
        ):
            await handler.handle(request_context, mock_responder)
            assert not mock_responder.messages

    @pytest.mark.asyncio
    async def test_disclosures_no_conn_id_no_thid(self, request_context):
        registry = ProtocolRegistry()
        registry.register_message_types({TEST_MESSAGE_TYPE: object()})
        request_context.injector.bind_instance(ProtocolRegistry, registry)
        disclosures = Disclosures(
            disclosures=[
                {
                    "id": DIDCommPrefix.qualify_current("basicmessage/1.0/message"),
                    "feature-type": "protocol",
                    "roles": [],
                },
                {"feature-type": "goal-code", "id": "aries.sell.goods.consumer"},
            ]
        )

        disclosures.assign_thread_id("test123")
        request_context.message = disclosures

        handler = DisclosuresHandler()
        mock_responder = MockResponder()
        with (
            mock.patch.object(
                V20DiscoveryExchangeRecord,
                "retrieve_by_id",
                mock.CoroutineMock(side_effect=StorageNotFoundError),
            ),
            mock.patch.object(
                V20DiscoveryExchangeRecord,
                "retrieve_by_connection_id",
                mock.CoroutineMock(side_effect=StorageNotFoundError),
            ),
        ):
            await handler.handle(request_context, mock_responder)
            assert not mock_responder.messages

    @pytest.mark.asyncio
    async def test_disclose_connection_not_ready(self, request_context):
        request_context.connection_ready = False
        disclosures = Disclosures(
            disclosures=[
                {
                    "id": DIDCommPrefix.qualify_current("basicmessage/1.0/message"),
                    "feature-type": "protocol",
                    "roles": [],
                },
                {"feature-type": "goal-code", "id": "aries.sell.goods.consumer"},
            ]
        )
        disclosures.assign_thread_id("test123")
        request_context.message = disclosures
        handler = DisclosuresHandler()
        mock_responder = MockResponder()
        with pytest.raises(HandlerException):
            await handler.handle(request_context, mock_responder)
