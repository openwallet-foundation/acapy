import pytest
import pytest_asyncio

from ......core.protocol_registry import ProtocolRegistry
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......tests import mock
from ......utils.testing import create_test_profile
from .....didcomm_prefix import DIDCommPrefix
from ...handlers.disclose_handler import DiscloseHandler
from ...messages.disclose import Disclose
from ...messages.query import Query
from ...models.discovery_record import V10DiscoveryExchangeRecord

TEST_MESSAGE_FAMILY = "doc/proto/1.0"
TEST_MESSAGE_TYPE = TEST_MESSAGE_FAMILY + "/message"


@pytest_asyncio.fixture
async def request_context():
    ctx = RequestContext.test_context(await create_test_profile())
    ctx.connection_ready = True
    ctx.connection_record = mock.MagicMock(connection_id="test123")
    yield ctx


class TestDiscloseHandler:
    @pytest.mark.asyncio
    async def test_disclose(self, request_context: RequestContext):
        registry = ProtocolRegistry()
        registry.register_message_types({TEST_MESSAGE_TYPE: object()})
        request_context.injector.bind_instance(ProtocolRegistry, registry)
        disclose_msg = Disclose(
            protocols=[
                {
                    "pid": DIDCommPrefix.qualify_current("test_proto/v1.0/test_message"),
                    "roles": [],
                }
            ]
        )
        query_msg = Query(query="*")
        discovery_record = V10DiscoveryExchangeRecord(
            connection_id="test123",
            thread_id="test123",
            query_msg=query_msg,
        )
        disclose_msg.assign_thread_id("test123")
        request_context.message = disclose_msg

        handler = DiscloseHandler()
        mock_responder = MockResponder()
        with mock.patch.object(
            V10DiscoveryExchangeRecord,
            "retrieve_by_id",
            mock.CoroutineMock(return_value=discovery_record),
        ):
            await handler.handle(request_context, mock_responder)
            assert not mock_responder.messages

    @pytest.mark.asyncio
    async def test_disclose_connection_not_ready(self, request_context):
        request_context.connection_ready = False
        disclose_msg = Disclose(
            protocols=[
                {
                    "pid": DIDCommPrefix.qualify_current("test_proto/v1.0/test_message"),
                    "roles": [],
                }
            ]
        )
        disclose_msg.assign_thread_id("test123")
        request_context.message = disclose_msg

        handler = DiscloseHandler()
        mock_responder = MockResponder()
        with pytest.raises(HandlerException):
            await handler.handle(request_context, mock_responder)
