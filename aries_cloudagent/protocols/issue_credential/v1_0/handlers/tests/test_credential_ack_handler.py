import pytest
from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.credential_ack import CredentialAck
from .. import credential_ack_handler as handler


class TestCredentialAckHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "CredentialManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_credential_ack = (
                async_mock.CoroutineMock()
            )
            request_context.message = CredentialAck()
            request_context.connection_ready = True
            handler_inst = handler.CredentialAckHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_cred_mgr.assert_called_once_with(request_context)
        mock_cred_mgr.return_value.receive_credential_ack.assert_called_once_with()
        assert not responder.messages

    async def test_called_not_ready(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "CredentialManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_credential_ack = (
                async_mock.CoroutineMock()
            )
            request_context.message = CredentialAck()
            request_context.connection_ready = False
            handler_inst = handler.CredentialAckHandler()
            responder = MockResponder()
            with self.assertRaises(handler.HandlerException):
                await handler_inst.handle(request_context, responder)

        assert not responder.messages
