import pytest

from ......core.protocol_registry import ProtocolRegistry
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder

from ...handlers.query_handler import QueryHandler
from ...messages.disclose import Disclose
from ...messages.query import Query

TEST_MESSAGE_FAMILY = "TEST_FAMILY"
TEST_MESSAGE_TYPE = TEST_MESSAGE_FAMILY + "/MESSAGE"


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    registry = ProtocolRegistry()
    registry.register_message_types({TEST_MESSAGE_TYPE: object()})
    ctx.injector.bind_instance(ProtocolRegistry, registry)
    yield ctx


class TestQueryHandler:
    @pytest.mark.asyncio
    async def test_query_all(self, request_context):
        request_context.message = Query(query="*")
        handler = QueryHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, Disclose) and result.protocols
        assert result.protocols[0]["pid"] == TEST_MESSAGE_FAMILY
        assert not target
