from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ......connections.models.conn_record import ConnRecord
from ......core.in_memory import InMemoryProfile
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...handlers.route_query_request_handler import RouteQueryRequestHandler
from ...handlers.route_update_request_handler import RouteUpdateRequestHandler
from ...handlers.route_query_response_handler import RouteQueryResponseHandler
from ...handlers.route_update_response_handler import RouteUpdateResponseHandler
from ...messages.route_query_request import RouteQueryRequest
from ...messages.route_query_response import RouteQueryResponse
from ...messages.route_update_request import RouteUpdateRequest
from ...messages.route_update_response import RouteUpdateResponse
from ...models.route_update import RouteUpdate
from ...models.route_updated import RouteUpdated

from .. import route_update_response_handler

TEST_CONN_ID = "conn-id"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"


class TestQueryUpdateHandlers(AsyncTestCase):
    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.context = RequestContext(self.profile)
        self.context.connection_ready = True
        self.context.connection_record = ConnRecord(connection_id="conn-id")
        self.context.message_receipt = MessageReceipt(sender_verkey=TEST_VERKEY)

    async def test_query_none(self):
        self.context.message = RouteQueryRequest()
        handler = RouteQueryRequestHandler()
        responder = MockResponder()
        await handler.handle(self.context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, RouteQueryResponse) and result.routes == []
        assert not target

    async def test_no_connection(self):
        self.context.connection_ready = False
        self.context.message = RouteQueryRequest()
        handler = RouteQueryRequestHandler()
        responder = MockResponder()
        with self.assertRaises(HandlerException):
            await handler.handle(self.context, responder)

        self.context.message = RouteUpdateRequest()
        handler = RouteUpdateRequestHandler()
        responder = MockResponder()
        with self.assertRaises(HandlerException):
            await handler.handle(self.context, responder)

        self.context.message = RouteQueryResponse()
        handler = RouteQueryResponseHandler()
        responder = MockResponder()
        with self.assertRaises(HandlerException):
            await handler.handle(self.context, responder)

        self.context.message = RouteUpdateResponse()
        handler = RouteUpdateResponseHandler()
        responder = MockResponder()
        with self.assertRaises(HandlerException):
            await handler.handle(self.context, responder)

    async def test_handle_update_query(self):
        self.context.message = RouteUpdateRequest(
            updates=[
                RouteUpdate(
                    recipient_key=TEST_VERKEY,
                    action=RouteUpdate.ACTION_CREATE,
                )
            ]
        )
        update_handler = RouteUpdateRequestHandler()
        update_responder = MockResponder()
        await update_handler.handle(self.context, update_responder)
        messages = update_responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, RouteUpdateResponse)
        assert len(result.updated) == 1
        assert result.updated[0].recipient_key == TEST_VERKEY
        assert result.updated[0].action == RouteUpdate.ACTION_CREATE
        assert result.updated[0].result == RouteUpdated.RESULT_SUCCESS
        assert not target

        self.context.message = RouteQueryRequest()
        query_handler = RouteQueryRequestHandler()
        query_responder = MockResponder()
        await query_handler.handle(self.context, query_responder)
        messages = query_responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, RouteQueryResponse)
        assert result.routes[0].recipient_key == TEST_VERKEY
        assert not target

    async def test_handle_response(self):
        messages = (
            [
                RouteUpdateResponse(
                    updated=[
                        RouteUpdated(
                            recipient_key=TEST_VERKEY,
                            action=RouteUpdate.ACTION_CREATE,
                            result=r,
                        )
                    ]
                )
                for r in [
                    RouteUpdated.RESULT_NO_CHANGE,
                    RouteUpdated.RESULT_SUCCESS,
                    RouteUpdated.RESULT_CLIENT_ERROR,
                    RouteUpdated.RESULT_SERVER_ERROR,
                ]
            ]
            + [
                RouteUpdateResponse(
                    updated=[
                        RouteUpdated(
                            recipient_key=TEST_VERKEY,
                            action=RouteUpdate.ACTION_DELETE,
                            result=RouteUpdated.RESULT_SUCCESS,
                        )
                    ]
                )
            ]
            + [
                RouteUpdateResponse(
                    updated=[
                        RouteUpdated(
                            recipient_key=TEST_VERKEY,
                            action="no such action",
                            result=RouteUpdated.RESULT_CLIENT_ERROR,
                        )
                    ]
                )
            ]
            + []
        )
        handler = RouteUpdateResponseHandler()
        for message in messages:
            self.context.message = message

            with async_mock.patch.object(
                route_update_response_handler, "ConnectionManager", autospec=True
            ) as mock_conn_mgr:
                mock_conn_mgr.return_value = async_mock.MagicMock()
                mock_conn_mgr.return_value.update_inbound = async_mock.CoroutineMock()

                await handler.handle(self.context, None)
