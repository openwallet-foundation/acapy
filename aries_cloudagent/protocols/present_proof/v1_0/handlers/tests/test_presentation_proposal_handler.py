import pytest
from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.presentation_proposal import PresentationProposal
from .. import presentation_proposal_handler as handler


class TestPresentationProposalHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.settings["debug.auto_respond_presentation_proposal"] = False

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_proposal = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
            request_context.message = PresentationProposal()
            request_context.connection_ready = True
            request_context.connection_record = async_mock.MagicMock()
            handler_inst = handler.PresentationProposalHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_pres_mgr.assert_called_once_with(request_context.profile)
        mock_pres_mgr.return_value.receive_proposal.assert_called_once_with(
            request_context.message, request_context.connection_record
        )
        assert not responder.messages

    async def test_called_auto_request(self):
        request_context = RequestContext.test_context()
        request_context.message = async_mock.MagicMock()
        request_context.message.comment = "hello world"
        request_context.message_receipt = MessageReceipt()
        request_context.settings["debug.auto_respond_presentation_proposal"] = True

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_proposal = async_mock.CoroutineMock(
                return_value="presentation_exchange_record"
            )
            mock_pres_mgr.return_value.create_bound_request = async_mock.CoroutineMock(
                return_value=(
                    mock_pres_mgr.return_value.receive_proposal.return_value,
                    "presentation_request_message",
                )
            )
            request_context.message = PresentationProposal()
            request_context.connection_ready = True
            handler_inst = handler.PresentationProposalHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_pres_mgr.assert_called_once_with(request_context.profile)
        mock_pres_mgr.return_value.create_bound_request.assert_called_once_with(
            presentation_exchange_record=(
                mock_pres_mgr.return_value.receive_proposal.return_value
            ),
            comment=request_context.message.comment,
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "presentation_request_message"
        assert target == {}

    async def test_called_not_ready(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_proposal = async_mock.CoroutineMock()
            request_context.message = PresentationProposal()
            request_context.connection_ready = False
            handler_inst = handler.PresentationProposalHandler()
            responder = MockResponder()
            with self.assertRaises(handler.HandlerException):
                await handler_inst.handle(request_context, responder)

        assert not responder.messages
