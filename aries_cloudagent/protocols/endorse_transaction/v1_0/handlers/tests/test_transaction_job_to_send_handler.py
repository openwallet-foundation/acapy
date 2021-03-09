from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...handlers import transaction_job_to_send_handler as handler
from ...messages.transaction_job_to_send import TransactionJobToSend


class TestTransactionJobToSendHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            handler, "TransactionManager", autospec=True
        ) as mock_tran_mgr:
            mock_tran_mgr.return_value.set_transaction_their_job = (
                async_mock.CoroutineMock()
            )
            request_context.message = TransactionJobToSend()
            request_context.connection_ready = True
            handler_inst = handler.TransactionJobToSendHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_tran_mgr.return_value.set_transaction_their_job.assert_called_once_with(
            request_context.message, request_context.message_receipt
        )
        assert not responder.messages

    async def test_called_not_ready(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            handler, "TransactionManager", autospec=True
        ) as mock_tran_mgr:
            mock_tran_mgr.return_value.set_transaction_their_job = (
                async_mock.CoroutineMock()
            )
            request_context.message = TransactionJobToSend()
            request_context.connection_ready = False
            handler_inst = handler.TransactionJobToSendHandler()
            responder = MockResponder()
            with self.assertRaises(handler.HandlerException):
                await handler_inst.handle(request_context, responder)

            assert not responder.messages
