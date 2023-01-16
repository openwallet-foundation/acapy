import pytest
from asynctest import mock as async_mock

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...manager import DIDXManagerError
from ...messages.complete import DIDXComplete
from ...messages.problem_report_reason import ProblemReportReason

from .. import complete_handler as test_module
from ......wallet.did_method import DIDMethods


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    ctx.injector.bind_instance(DIDMethods, DIDMethods())
    ctx.message_receipt = MessageReceipt()
    yield ctx


class TestDIDXCompleteHandler:
    """Class unit testing complete handler."""

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "DIDXManager")
    async def test_called(self, mock_conn_mgr, request_context):
        mock_conn_mgr.return_value.accept_complete = async_mock.CoroutineMock()
        request_context.message = DIDXComplete()
        handler_inst = test_module.DIDXCompleteHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, None)

        mock_conn_mgr.return_value.accept_complete.assert_called_once_with(
            request_context.message, request_context.message_receipt
        )

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "DIDXManager")
    async def test_x(self, mock_conn_mgr, request_context):
        mock_conn_mgr.return_value.accept_complete = async_mock.CoroutineMock(
            side_effect=DIDXManagerError(
                error_code=ProblemReportReason.COMPLETE_NOT_ACCEPTED.value
            )
        )
        mock_conn_mgr.return_value._logger = async_mock.MagicMock(
            exception=async_mock.MagicMock()
        )
        request_context.message = DIDXComplete()
        handler_inst = test_module.DIDXCompleteHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)

        assert mock_conn_mgr.return_value._logger.exception.called_once_(
            "Error receiving connection complete"
        )
