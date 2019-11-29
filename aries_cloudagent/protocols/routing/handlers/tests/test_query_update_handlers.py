import pytest

from .....connections.models.connection_record import ConnectionRecord
from .....messaging.base_handler import HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import MockResponder
from .....storage.base import BaseStorage
from .....storage.basic import BasicStorage
from .....transport.inbound.receipt import MessageReceipt

from ...handlers.route_query_request_handler import RouteQueryRequestHandler
from ...handlers.route_update_request_handler import RouteUpdateRequestHandler
from ...messages.route_query_request import RouteQueryRequest
from ...messages.route_query_response import RouteQueryResponse
from ...messages.route_update_request import RouteUpdateRequest
from ...messages.route_update_response import RouteUpdateResponse
from ...models.route_update import RouteUpdate
from ...models.route_updated import RouteUpdated

TEST_CONN_ID = "conn-id"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext()
    ctx.connection_ready = True
    ctx.connection_record = ConnectionRecord(connection_id="conn-id")
    ctx.message_receipt = MessageReceipt(sender_verkey=TEST_VERKEY)
    ctx.injector.bind_instance(BaseStorage, BasicStorage())
    yield ctx


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
        assert isinstance(result, RouteQueryResponse) and result.routes == []
        assert not target

    @pytest.mark.asyncio
    async def test_no_connection(self, request_context):
        request_context.connection_ready = False
        request_context.message = RouteQueryRequest()
        handler = RouteQueryRequestHandler()
        responder = MockResponder()
        with pytest.raises(HandlerException):
            await handler.handle(request_context, responder)

        request_context.message = RouteUpdateRequest()
        handler = RouteUpdateRequestHandler()
        responder = MockResponder()
        with pytest.raises(HandlerException):
            await handler.handle(request_context, responder)

    @pytest.mark.asyncio
    async def test_query_route(self, request_context):
        request_context.message = RouteUpdateRequest(
            updates=[
                RouteUpdate(recipient_key=TEST_VERKEY, action=RouteUpdate.ACTION_CREATE)
            ]
        )
        update_handler = RouteUpdateRequestHandler()
        update_responder = MockResponder()
        await update_handler.handle(request_context, update_responder)
        messages = update_responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, RouteUpdateResponse)
        assert len(result.updated) == 1
        assert result.updated[0].recipient_key == TEST_VERKEY
        assert result.updated[0].action == RouteUpdate.ACTION_CREATE
        assert result.updated[0].result == RouteUpdated.RESULT_SUCCESS
        assert not target

        request_context.message = RouteQueryRequest()
        query_handler = RouteQueryRequestHandler()
        query_responder = MockResponder()
        await query_handler.handle(request_context, query_responder)
        messages = query_responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, RouteQueryResponse)
        assert result.routes[0].recipient_key == TEST_VERKEY
        assert not target
