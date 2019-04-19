import pytest

from ....responder import BaseResponder
from ....connections.models.connection_record import ConnectionRecord
from ...handlers.route_query_request_handler import RouteQueryRequestHandler
from .....messaging.request_context import RequestContext
from ...messages.route_query_request import RouteQueryRequest
from ...messages.route_update_request import RouteUpdateRequest
from ...models.route_update import RouteUpdate
from .....storage.basic import BasicStorage

TEST_CONN_ID = "conn-id"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext()
    ctx.connection_active = True
    ctx.connection_record = ConnectionRecord(connection_id="conn-id")
    ctx.sender_verkey = TEST_VERKEY
    ctx.storage = BasicStorage()
    yield ctx


class MockResponder(BaseResponder):
    def __init__(self):
        self.messages = []

    async def send_reply(self, message):
        self.messages.append((message, None))

    async def send_outbound(self, message, target):
        self.messages.append((message, target))


class TestQueryUpdateHandlers:
    @pytest.mark.asyncio
    async def test_query_none(self, request_context):
        request_context.message = RouteQueryRequest()
        handler = RouteQueryRequestHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert result.routes == []
        assert target is None

    @pytest.mark.asyncio
    async def test_query_route(self, request_context):
        request_context.message = RouteUpdateRequest()
        update_handler = RouteQueryRequestHandler()
        update_responder = MockResponder()

        request_context.message = RouteQueryRequest()
        query_handler = RouteQueryRequestHandler()
        query_responder = MockResponder()
        await query_handler.handle(request_context, query_responder)
        messages = query_responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert result.routes == []
        assert target is None
