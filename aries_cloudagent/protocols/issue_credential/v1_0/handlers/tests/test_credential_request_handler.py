import pytest
from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.credential_request import CredentialRequest
from .. import credential_request_handler as handler


class TestCredentialRequestHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "CredentialManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
            mock_cred_mgr.return_value.receive_request.return_value.auto_issue = False
            request_context.message = CredentialRequest()
            request_context.connection_ready = True
            handler_inst = handler.CredentialRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_cred_mgr.assert_called_once_with(request_context)
        mock_cred_mgr.return_value.receive_request.assert_called_once_with()
        assert not responder.messages

    async def test_called_auto_issue(self):
        request_context = RequestContext()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            handler, "CredentialManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            handler, "CredentialProposal", autospec=True
        ) as mock_cred_proposal:
            mock_cred_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
            mock_cred_mgr.return_value.receive_request.return_value.auto_issue = True
            mock_cred_mgr.return_value.issue_credential = async_mock.CoroutineMock(
                return_value=(None, "credential_issue_message")
            )
            mock_cred_proposal.deserialize = async_mock.MagicMock(
                return_value=mock_cred_proposal
            )
            mock_cred_proposal.credential_proposal = async_mock.MagicMock()
            mock_cred_proposal.credential_proposal.attr_dict = async_mock.MagicMock()
            request_context.message = CredentialRequest()
            request_context.connection_ready = True
            handler_inst = handler.CredentialRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_cred_mgr.assert_called_once_with(request_context)
        mock_cred_mgr.return_value.receive_request.assert_called_once_with()
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "credential_issue_message"
        assert target == {}

    async def test_called_not_ready(self):
        request_context = RequestContext()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "CredentialManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_request = async_mock.CoroutineMock()
            request_context.message = CredentialRequest()
            request_context.connection_ready = False
            handler_inst = handler.CredentialRequestHandler()
            responder = MockResponder()
            with self.assertRaises(handler.HandlerException):
                await handler_inst.handle(request_context, responder)

        assert not responder.messages
