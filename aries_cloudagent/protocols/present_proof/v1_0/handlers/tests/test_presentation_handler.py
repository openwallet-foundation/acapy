import pytest
from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.presentation import Presentation
from .. import presentation_handler as handler


class TestPresentationHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.settings["debug.auto_verify_presentation"] = False

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            request_context, "session", async_mock.CoroutineMock()
        ) as mock_session:
            mock_pres_mgr.return_value.receive_presentation = async_mock.CoroutineMock()
            request_context.message = Presentation()
            request_context.connection_ready = True
            request_context.connection_record = async_mock.MagicMock()
            handler_inst = handler.PresentationHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_pres_mgr.assert_called_once_with(mock_session.return_value)
        mock_pres_mgr.return_value.receive_presentation.assert_called_once_with(
            request_context.message, request_context.connection_record
        )
        assert not responder.messages

    async def test_called_auto_verify(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.settings["debug.auto_verify_presentation"] = True

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            request_context, "session", async_mock.CoroutineMock()
        ) as mock_session:
            mock_pres_mgr.return_value.receive_presentation = async_mock.CoroutineMock()
            mock_pres_mgr.return_value.verify_presentation = async_mock.CoroutineMock()
            request_context.message = Presentation()
            request_context.connection_ready = True
            request_context.connection_record = async_mock.MagicMock()
            handler_inst = handler.PresentationHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_pres_mgr.assert_called_once_with(mock_session.return_value)
        mock_pres_mgr.return_value.receive_presentation.assert_called_once_with(
            request_context.message, request_context.connection_record
        )
        assert not responder.messages
