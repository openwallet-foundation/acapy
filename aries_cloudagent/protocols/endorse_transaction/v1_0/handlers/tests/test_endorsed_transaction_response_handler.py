import pytest
from asynctest import mock as async_mock

from ......messaging.request_context import RequestContext
from ......core.profile import Profile
from ......messaging.responder import MockResponder

from ...handlers import endorsed_transaction_response_handler as handler
from ...messages.endorsed_transaction_response import EndorsedTransactionResponse


@pytest.fixture()
async def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    yield ctx


@pytest.fixture()
async def profile(request_context) -> Profile:
    yield await request_context.profile


class TestEndorsedTransactionResponseHandler:
    @pytest.mark.asyncio
    @async_mock.patch.object(handler, "TransactionManager")
    async def test_called(self, mock_tran_mgr, request_context):
        mock_tran_mgr.return_value.receive_endorse_response = async_mock.CoroutineMock()
        request_context.message = EndorsedTransactionResponse()
        handler_inst = handler.EndorsedTransactionResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)
        mock_tran_mgr.return_value.receive_endorse_response.assert_called_once_with(
            request_context.message
        )
