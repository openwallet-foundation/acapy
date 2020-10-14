import pytest
from asynctest import mock as async_mock

from aries_cloudagent.connections.models import connection_target
from aries_cloudagent.messaging.base_handler import HandlerException
from aries_cloudagent.messaging.request_context import RequestContext
from aries_cloudagent.transport.inbound.receipt import MessageReceipt

from ...handlers import request_handler as test_module
from ...manager import Conn23ManagerError
from ...messages.complete import Conn23Complete


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext()
    ctx.message_receipt = MessageReceipt()
    yield ctx


class TestConn23CompleteHandler:
    """Class unit testing complete handler."""

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "Conn23Manager")
    async def test_called(self, mock_conn_mgr, request_context):
        mock_conn_mgr.return_value.accept_complete = async_mock.CoroutineMock()
        request_context.message = Conn23Complete()
        handler_inst = test_module.Conn23CompleteHandler()

        mock_conn_mgr.assert_called_once_with(request_context)
        mock_conn_mgr.return_value.accept_complete.assert_called_once_with(
            request_context.message, request_context.message_receipt
        )

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "Conn23Manager")
    async def test_x(self, mock_conn_mgr):
        mock_conn_mgr.return_value.accept_complete = async_mock.CoroutineMock()
        mock_conn_mgr.return_value.accept_complete.side_effect = Conn23ManagerError(
            error_code=ProblemReportReason.COMPLETE_NOT_ACCEPTED
        )
        mock_conn_mgr.return_value._logger = async_mock.MagicMock(
            exception=async_mock.MagicMock()
        )
        request_context.message = Conn23Complete()
        handler_inst = test_module.Conn23CompleteHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)
        assert mock_conn_mgr.return_value._logger.exception.called_once_(
            "Error receiving connection complete"
        )
