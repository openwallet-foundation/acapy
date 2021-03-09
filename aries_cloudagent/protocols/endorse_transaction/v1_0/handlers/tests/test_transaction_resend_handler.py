from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...handlers import transaction_resend_handler as handler
from ...messages.transaction_resend import TransactionResend
from ......connections.models.conn_record import ConnRecord


class TestTransactionResendHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "TransactionManager", autospec=True
        ) as mock_tran_mgr:
            mock_tran_mgr.return_value.receive_transaction_resend = (
                async_mock.CoroutineMock()
            )
            request_context.message = TransactionResend()
            request_context.connection_record = ConnRecord(
                connection_id="b5dc1636-a19a-4209-819f-e8f9984d9897"
            )
            request_context.connection_ready = True
            handler_inst = handler.TransactionResendHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_tran_mgr.return_value.receive_transaction_resend.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        assert not responder.messages

    async def test_called_not_ready(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            handler, "TransactionManager", autospec=True
        ) as mock_tran_mgr:
            mock_tran_mgr.return_value.receive_transaction_resend = (
                async_mock.CoroutineMock()
            )
            request_context.message = TransactionResend()
            request_context.connection_ready = False
            handler_inst = handler.TransactionResendHandler()
            responder = MockResponder()
            with self.assertRaises(handler.HandlerException):
                await handler_inst.handle(request_context, responder)

            assert not responder.messages
