import pytest
from asynctest import mock as async_mock

from .....messaging.base_handler import HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import MockResponder
from .....transport.inbound.receipt import MessageReceipt

from ...handlers import connection_response_handler as handler
from ...manager import ConnectionManagerError
from ...messages.connection_response import ConnectionResponse
from ...messages.problem_report import ProblemReport, ProblemReportReason


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext()
    ctx.message_receipt = MessageReceipt()
    yield ctx


class TestResponseHandler:
    @pytest.mark.asyncio
    @async_mock.patch.object(handler, "ConnectionManager")
    async def test_called(self, mock_conn_mgr, request_context):
        mock_conn_mgr.return_value.accept_response = async_mock.CoroutineMock()
        request_context.message = ConnectionResponse()
        handler_inst = handler.ConnectionResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)

        mock_conn_mgr.assert_called_once_with(request_context)
        mock_conn_mgr.return_value.accept_response.assert_called_once_with(
            request_context.message, request_context.message_receipt
        )
        assert not responder.messages

    @pytest.mark.asyncio
    @async_mock.patch.object(handler, "ConnectionManager")
    async def test_problem_report(self, mock_conn_mgr, request_context):
        mock_conn_mgr.return_value.accept_response = async_mock.CoroutineMock()
        mock_conn_mgr.return_value.accept_response.side_effect = ConnectionManagerError(
            error_code=ProblemReportReason.RESPONSE_NOT_ACCEPTED
        )
        request_context.message = ConnectionResponse()
        handler_inst = handler.ConnectionResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, ProblemReport)
            and result.problem_code == ProblemReportReason.RESPONSE_NOT_ACCEPTED
        )
        assert target == {"target_list": None}
