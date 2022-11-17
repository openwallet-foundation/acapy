from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...handlers import refused_transaction_response_handler as test_module
from ...messages.refused_transaction_response import RefusedTransactionResponse


class TestRefusedTransactionResponseHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "TransactionManager", autospec=True
        ) as mock_tran_mgr:
            mock_tran_mgr.return_value.receive_refuse_response = (
                async_mock.CoroutineMock()
            )
            request_context.message = RefusedTransactionResponse()
            request_context.connection_ready = True
            handler = test_module.RefusedTransactionResponseHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_tran_mgr.return_value.receive_refuse_response.assert_called_once_with(
            request_context.message
        )
        assert not responder.messages

    async def test_called_not_ready(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "TransactionManager", autospec=True
        ) as mock_tran_mgr:
            mock_tran_mgr.return_value.receive_refuse_response = (
                async_mock.CoroutineMock()
            )
            request_context.message = RefusedTransactionResponse()
            request_context.connection_ready = False
            handler = test_module.RefusedTransactionResponseHandler()
            responder = MockResponder()
            with self.assertRaises(test_module.HandlerException):
                await handler.handle(request_context, responder)

            assert not responder.messages

    async def test_called_x(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "TransactionManager", autospec=True
        ) as mock_tran_mgr:
            mock_tran_mgr.return_value.receive_refuse_response = (
                async_mock.CoroutineMock(
                    side_effect=test_module.TransactionManagerError()
                )
            )
            request_context.message = RefusedTransactionResponse()
            request_context.connection_ready = True
            handler = test_module.RefusedTransactionResponseHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_tran_mgr.return_value.receive_refuse_response.assert_called_once_with(
            request_context.message
        )
        assert not responder.messages
