from aries_cloudagent.tests import mock
from unittest import IsolatedAsyncioTestCase

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.cred_proposal import V20CredProposal

from .. import cred_proposal_handler as test_module


class TestV20CredProposalHandler(IsolatedAsyncioTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = mock.MagicMock()

        with mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_proposal = mock.CoroutineMock(
                return_value=mock.MagicMock()
            )
            mock_cred_mgr.return_value.receive_proposal.return_value.auto_offer = False
            request_context.message = V20CredProposal()
            request_context.connection_ready = True
            handler_inst = test_module.V20CredProposalHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_cred_mgr.assert_called_once_with(request_context.profile)
        mock_cred_mgr.return_value.receive_proposal.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        assert not responder.messages

    async def test_called_auto_offer(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = mock.MagicMock()

        with mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_proposal = mock.CoroutineMock(
                return_value=mock.MagicMock()
            )
            mock_cred_mgr.return_value.receive_proposal.return_value.auto_offer = True
            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock(
                return_value=(None, "cred_offer_message")
            )
            request_context.message = V20CredProposal()
            request_context.connection_ready = True
            handler_inst = test_module.V20CredProposalHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_cred_mgr.assert_called_once_with(request_context.profile)
        mock_cred_mgr.return_value.receive_proposal.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "cred_offer_message"
        assert target == {}

    async def test_called_auto_offer_x_indy(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = mock.MagicMock()

        with mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_proposal = mock.CoroutineMock(
                return_value=mock.MagicMock(save_error_state=mock.CoroutineMock())
            )
            mock_cred_mgr.return_value.receive_proposal.return_value.auto_offer = True
            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock(
                side_effect=test_module.IndyIssuerError()
            )

            request_context.message = V20CredProposal()
            request_context.connection_ready = True
            handler = test_module.V20CredProposalHandler()
            responder = MockResponder()

            with mock.patch.object(
                responder, "send_reply", mock.CoroutineMock()
            ) as mock_send_reply, mock.patch.object(
                handler._logger, "exception", mock.MagicMock()
            ) as mock_log_exc:
                await handler.handle(request_context, responder)
                mock_log_exc.assert_called_once()

    async def test_called_auto_offer_x_anoncreds(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = mock.MagicMock()

        with mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_proposal = mock.CoroutineMock(
                return_value=mock.MagicMock(save_error_state=mock.CoroutineMock())
            )
            mock_cred_mgr.return_value.receive_proposal.return_value.auto_offer = True
            mock_cred_mgr.return_value.create_offer = mock.AsyncMock(
                side_effect=test_module.AnonCredsIssuerError()
            )

            request_context.message = V20CredProposal()
            request_context.connection_ready = True
            handler = test_module.V20CredProposalHandler()
            responder = MockResponder()

            with mock.patch.object(
                responder, "send_reply", mock.CoroutineMock()
            ) as mock_send_reply, mock.patch.object(
                handler._logger, "exception", mock.MagicMock()
            ) as mock_log_exc:
                await handler.handle(request_context, responder)
                mock_log_exc.assert_called_once()

    async def test_called_not_ready(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = mock.MagicMock()

        with mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_proposal = mock.CoroutineMock()
            request_context.message = V20CredProposal()
            request_context.connection_ready = False
            handler_inst = test_module.V20CredProposalHandler()
            responder = MockResponder()
            with self.assertRaises(test_module.HandlerException) as err:
                await handler_inst.handle(request_context, responder)
            assert (
                err.exception.message
                == "Connection used for credential proposal not ready"
            )

        assert not responder.messages

    async def test_called_no_connection(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()

        request_context.message = V20CredProposal()
        handler_inst = test_module.V20CredProposalHandler()
        responder = MockResponder()
        with self.assertRaises(test_module.HandlerException) as err:
            await handler_inst.handle(request_context, responder)
        assert (
            err.exception.message
            == "Connectionless not supported for credential proposal"
        )

        assert not responder.messages
