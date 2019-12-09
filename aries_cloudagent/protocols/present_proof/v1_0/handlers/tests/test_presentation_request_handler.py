import pytest
from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......storage.error import StorageNotFoundError
from ......transport.inbound.receipt import MessageReceipt

from ...messages.presentation_request import PresentationRequest
from .. import presentation_request_handler as handler


class TestPresentationRequestHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message_receipt = MessageReceipt()
        request_context.message = PresentationRequest()
        request_context.message.indy_proof_request = async_mock.MagicMock(
            return_value=async_mock.MagicMock()
        )

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            handler, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex_rec:

            mock_pres_ex_rec.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=mock_pres_ex_rec
            )

            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
            mock_pres_mgr.return_value.receive_request.return_value.auto_present = False

            request_context.connection_ready = True
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_pres_mgr.assert_called_once_with(request_context)
        mock_pres_mgr.return_value.receive_request.assert_called_once_with(
            mock_pres_ex_rec
        )
        assert not responder.messages

    async def test_called_not_found(self):
        request_context = RequestContext()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message_receipt = MessageReceipt()
        request_context.message = PresentationRequest()
        request_context.message.indy_proof_request = async_mock.MagicMock(
            return_value=async_mock.MagicMock()
        )

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            handler, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex_rec:

            mock_pres_ex_rec.retrieve_by_tag_filter = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )
            mock_pres_ex_rec.return_value = mock_pres_ex_rec

            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
            mock_pres_mgr.return_value.receive_request.return_value.auto_present = False

            request_context.connection_ready = True
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_pres_mgr.assert_called_once_with(request_context)
        mock_pres_mgr.return_value.receive_request.assert_called_once_with(
            mock_pres_ex_rec
        )
        assert not responder.messages

    async def test_called_auto_present(self):
        request_context = RequestContext()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = PresentationRequest()
        request_context.message.indy_proof_request = async_mock.MagicMock(
            return_value=async_mock.MagicMock()
        )
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            handler, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex_rec, async_mock.patch.object(
            handler, "BaseHolder", autospec=True
        ) as mock_holder:

            request_context.inject = async_mock.CoroutineMock(return_value=mock_holder)

            mock_pres_ex_rec.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=mock_pres_ex_rec
            )

            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=mock_pres_ex_rec
            )
            mock_pres_mgr.return_value.receive_request.return_value.auto_present = True

            handler.indy_proof_request2indy_requested_creds = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )

            mock_pres_mgr.return_value.create_presentation = async_mock.CoroutineMock(
                return_value=(mock_pres_ex_rec, "presentation_message")
            )
            request_context.connection_ready = True
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)
            mock_pres_mgr.return_value.create_presentation.assert_called_once()

        mock_pres_mgr.assert_called_once_with(request_context)
        mock_pres_mgr.return_value.receive_request.assert_called_once_with(
            mock_pres_ex_rec
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "presentation_message"
        assert target == {}

    async def test_called_auto_present_value_error(self):
        request_context = RequestContext()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = PresentationRequest()
        request_context.message.indy_proof_request = async_mock.MagicMock(
            return_value=async_mock.MagicMock()
        )
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            handler, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex_rec, async_mock.patch.object(
            handler, "BaseHolder", autospec=True
        ) as mock_holder:

            request_context.inject = async_mock.CoroutineMock(return_value=mock_holder)

            mock_pres_ex_rec.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=mock_pres_ex_rec
            )

            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=mock_pres_ex_rec
            )
            mock_pres_mgr.return_value.receive_request.return_value.auto_present = True

            handler.indy_proof_request2indy_requested_creds = async_mock.CoroutineMock(
                side_effect=ValueError
            )

            mock_pres_mgr.return_value.create_presentation = async_mock.CoroutineMock(
                return_value=(mock_pres_ex_rec, "presentation_message")
            )
            request_context.connection_ready = True
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)
            mock_pres_mgr.return_value.create_presentation.assert_not_called()

        mock_pres_mgr.assert_called_once_with(request_context)
        mock_pres_mgr.return_value.receive_request.assert_called_once_with(
            mock_pres_ex_rec
        )
        assert not responder.messages

    async def test_called_not_ready(self):
        request_context = RequestContext()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock()
            request_context.message = PresentationRequest()
            request_context.connection_ready = False
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            with self.assertRaises(handler.HandlerException):
                await handler_inst.handle(request_context, responder)

        assert not responder.messages
