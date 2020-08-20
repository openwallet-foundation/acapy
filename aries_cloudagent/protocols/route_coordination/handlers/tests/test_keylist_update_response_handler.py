import pytest
from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from .....messaging.request_context import RequestContext
from .....messaging.responder import MockResponder
from .....transport.inbound.receipt import MessageReceipt

from ...messages.keylist_update_response import KeylistUpdateResponse
from ...handlers import keylist_update_response_handler as handler


class TestKeylistUpdateResponseHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "RouteCoordinationManager", autospec=True
        ) as mock_route_mgr:
        #     mock_route_mgr.return_value.receive_proposal = async_mock.CoroutineMock(
        #         return_value="presentation_exchange_record"
        #     )
        #     mock_pres_mgr.return_value.create_bound_request = async_mock.CoroutineMock(
        #         return_value=(
        #             "server_error",
        #             "client_error",
        #         )
        #     )
        #     request_context.message = PresentationProposal()
        #     request_context.connection_ready = True
        #     handler_inst = handler.PresentationProposalHandler()
        #     responder = MockResponder()
        #     await handler_inst.handle(request_context, responder)

        # mock_pres_mgr.assert_called_once_with(request_context)
        # mock_pres_mgr.return_value.create_bound_request.assert_called_once_with(
        #     presentation_exchange_record=(
        #         mock_pres_mgr.return_value.receive_proposal.return_value
        #     ),
        #     comment=request_context.message.comment,
        # )
        # messages = responder.messages
        # assert len(messages) == 1
        # (result, target) = messages[0]
        # assert result == "presentation_request_message"
        # assert target == {}







            mock_route_mgr.return_value.receive_keylist_update_response = (
                async_mock.CoroutineMock(return_value=(
                    "server_error",
                    "client_error",
                    )
                )
            )
            request_context.message = KeylistUpdateResponse()
            request_context.connection_record = async_mock.MagicMock()
            request_context.connection_ready = True
            handler_inst = handler.KeylistUpdateResponseHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_route_mgr.assert_called_once_with(request_context)
        mock_route_mgr.return_value.receive_keylist_update_response.assert_called_once_with()
        assert not responder.messages

    async def test_called_not_ready(self):
        request_context = RequestContext()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "RouteCoordinationManager", autospec=True
        ) as mock_route_mgr:
            mock_route_mgr.return_value.receive_keylist_update_response = (
                async_mock.CoroutineMock()
            )
            request_context.message = KeylistUpdateResponse()
            request_context.connection_ready = False
            handler_inst = handler.KeylistUpdateResponseHandler()
            responder = MockResponder()
            with self.assertRaises(handler.HandlerException):
                await handler_inst.handle(request_context, responder)

        assert not responder.messages
