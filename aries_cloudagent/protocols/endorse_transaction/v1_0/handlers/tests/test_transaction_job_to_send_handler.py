import pytest
from asynctest import mock as async_mock

from ......messaging.request_context import RequestContext
from ......core.profile import Profile, ProfileSession
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...handlers import transaction_job_to_send_handler as handler
from ...messages.transaction_job_to_send import TransactionJobToSend


@pytest.fixture()
async def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    ctx.message_receipt = MessageReceipt()
    yield ctx


@pytest.fixture()
async def session(request_context) -> ProfileSession:
    yield await request_context.session()


@pytest.fixture()
async def profile(request_context) -> Profile:
    yield await request_context.profile


class TestTransactionJobToSendHandler:
    @pytest.mark.asyncio
    @async_mock.patch.object(handler, "TransactionManager")
    async def test_called(self, mock_tran_mgr, request_context):
        mock_tran_mgr.return_value.set_transaction_their_job = (
            async_mock.CoroutineMock()
        )
        request_context.message = TransactionJobToSend()
        handler_inst = handler.TransactionJobToSendHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)
        mock_tran_mgr.return_value.set_transaction_their_job.assert_called_once_with(
            request_context.message, request_context.message_receipt
        )
