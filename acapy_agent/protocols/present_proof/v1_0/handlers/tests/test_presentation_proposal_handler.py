from unittest import IsolatedAsyncioTestCase

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......tests import mock
from ......transport.inbound.receipt import MessageReceipt
from ......utils.testing import create_test_profile
from ...messages.presentation_proposal import PresentationProposal
from .. import presentation_proposal_handler as test_module


class TestPresentationProposalHandler(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile()
        self.request_context = RequestContext.test_context(self.profile)
        self.request_context.message_receipt = MessageReceipt()
        self.request_context.settings["debug.auto_respond_presentation_proposal"] = False
        self.request_context.connection_record = mock.MagicMock()
        self.request_context.message = mock.MagicMock()
        self.request_context.message.comment = "hello world"

    async def test_called(self):
        with mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_proposal = mock.CoroutineMock(
                return_value=mock.MagicMock()
            )
            self.request_context.message = PresentationProposal()
            self.request_context.connection_ready = True
            self.request_context.connection_record = mock.MagicMock()
            handler = test_module.PresentationProposalHandler()
            responder = MockResponder()
            await handler.handle(self.request_context, responder)

        mock_pres_mgr.assert_called_once_with(self.request_context.profile)
        mock_pres_mgr.return_value.receive_proposal.assert_called_once_with(
            self.request_context.message, self.request_context.connection_record
        )
        assert not responder.messages

    async def test_called_auto_request(self):
        self.request_context.settings["debug.auto_respond_presentation_proposal"] = True
        with mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_proposal = mock.CoroutineMock(
                return_value="presentation_exchange_record"
            )
            mock_pres_mgr.return_value.create_bound_request = mock.CoroutineMock(
                return_value=(
                    mock_pres_mgr.return_value.receive_proposal.return_value,
                    "presentation_request_message",
                )
            )
            self.request_context.message = PresentationProposal()
            self.request_context.connection_ready = True
            handler = test_module.PresentationProposalHandler()
            responder = MockResponder()
            await handler.handle(self.request_context, responder)

        mock_pres_mgr.assert_called_once_with(self.request_context.profile)
        mock_pres_mgr.return_value.create_bound_request.assert_called_once_with(
            presentation_exchange_record=(
                mock_pres_mgr.return_value.receive_proposal.return_value
            ),
            comment=self.request_context.message.comment,
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "presentation_request_message"
        assert target == {}

    async def test_called_auto_request_x(self):
        with mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_proposal = mock.CoroutineMock(
                return_value=mock.MagicMock(save_error_state=mock.CoroutineMock())
            )
            mock_pres_mgr.return_value.create_bound_request = mock.CoroutineMock(
                side_effect=test_module.LedgerError()
            )

            self.request_context.message = PresentationProposal()
            self.request_context.connection_ready = True
            handler = test_module.PresentationProposalHandler()
            responder = MockResponder()

            await handler.handle(self.request_context, responder)

    async def test_called_not_ready(self):
        with mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_proposal = mock.CoroutineMock()
            self.request_context.message = PresentationProposal()
            self.request_context.connection_ready = False
            handler = test_module.PresentationProposalHandler()
            responder = MockResponder()
            with self.assertRaises(test_module.HandlerException) as err:
                await handler.handle(self.request_context, responder)
        assert (
            err.exception.message == "Connection used for presentation proposal not ready"
        )

        assert not responder.messages

    async def test_called_no_connection(self):
        self.request_context.message = PresentationProposal()
        self.request_context.connection_record = None
        handler = test_module.PresentationProposalHandler()
        responder = MockResponder()
        with self.assertRaises(test_module.HandlerException) as err:
            await handler.handle(self.request_context, responder)
        assert (
            err.exception.message
            == "Connectionless not supported for presentation proposal"
        )

        assert not responder.messages
