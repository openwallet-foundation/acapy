import pytest

from ....base_handler import HandlerException
from ....message_factory import MessageFactory
from ....request_context import RequestContext
from ....responder import BaseResponder

from ...handlers.query_handler import QueryHandler
from ...messages.disclose import Disclose
from ...messages.query import Query

TEST_MESSAGE_FAMILY = "TEST_FAMILY"
TEST_MESSAGE_TYPE = TEST_MESSAGE_FAMILY + "/MESSAGE"


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext()
    factory = MessageFactory()
    factory.register_message_types({TEST_MESSAGE_TYPE: object()})
    ctx.injector.bind_instance(MessageFactory, factory)
    yield ctx


class MockResponder(BaseResponder):
    def __init__(self):
        self.messages = []

    async def send_reply(self, message):
        self.messages.append((message, None))

    async def send_outbound(self, message, target):
        self.messages.append((message, target))


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
        assert isinstance(result, Disclose) and result.protocols == {
            TEST_MESSAGE_FAMILY: {}
        }
        assert target is None
