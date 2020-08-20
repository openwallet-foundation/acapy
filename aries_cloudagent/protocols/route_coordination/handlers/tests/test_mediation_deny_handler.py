import pytest
from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from .....messaging.request_context import RequestContext
from .....messaging.responder import MockResponder
from .....transport.inbound.receipt import MessageReceipt

from ...messages.mediation_deny import MediationDeny
from ...handlers import mediation_deny_handler as handler


class TestMediationDenyHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "RouteCoordinationManager", autospec=True
        ) as mock_route_mgr:
            mock_route_mgr.return_value.receive_mediation_deny = (
                async_mock.CoroutineMock()
            )
            request_context.message = MediationDeny()
            request_context.connection_ready = True
            handler_inst = handler.MediationDenyHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_route_mgr.assert_called_once_with(request_context)
        mock_route_mgr.return_value.receive_mediation_deny.assert_called_once_with()
        assert not responder.messages

    async def test_called_not_ready(self):
        request_context = RequestContext()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "RouteCoordinationManager", autospec=True
        ) as mock_route_mgr:
            mock_route_mgr.return_value.receive_mediation_deny = (
                async_mock.CoroutineMock()
            )
            request_context.message = MediationDeny()
            request_context.connection_ready = False
            handler_inst = handler.MediationDenyHandler()
            responder = MockResponder()
            with self.assertRaises(handler.HandlerException):
                await handler_inst.handle(request_context, responder)

        assert not responder.messages
