from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.presentation_ack import PresentationAck
from .. import presentation_ack_handler as handler


class TestPresentationAckHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        session = request_context.session()

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_presentation_ack = (
                async_mock.CoroutineMock()
            )
            request_context.message = PresentationAck()
            request_context.connection_ready = True
            request_context.connection_record = async_mock.MagicMock()
            handler_inst = handler.PresentationAckHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_pres_mgr.assert_called_once_with(request_context.profile)
        mock_pres_mgr.return_value.receive_presentation_ack.assert_called_once_with(
            request_context.message, request_context.connection_record
        )
        assert not responder.messages

    async def test_called_not_ready(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_presentation_ack = (
                async_mock.CoroutineMock()
            )
            request_context.message = PresentationAck()
            request_context.connection_ready = False
            handler_inst = handler.PresentationAckHandler()
            responder = MockResponder()
            with self.assertRaises(handler.HandlerException):
                await handler_inst.handle(request_context, responder)

        assert not responder.messages
