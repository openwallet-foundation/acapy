import pytest
import pytest_asyncio

from acapy_agent.tests import mock

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt
from ......utils.testing import create_test_profile
from ......wallet.did_method import DIDMethods
from ...manager import DIDXManagerError
from ...messages.complete import DIDXComplete
from ...messages.problem_report import ProblemReportReason
from .. import complete_handler as test_module


@pytest_asyncio.fixture
async def request_context():
    ctx = RequestContext.test_context(await create_test_profile())
    ctx.injector.bind_instance(DIDMethods, DIDMethods())
    ctx.message_receipt = MessageReceipt()
    yield ctx


class TestDIDXCompleteHandler:
    """Class unit testing complete handler."""

    @pytest.mark.asyncio
    @mock.patch.object(test_module, "DIDXManager")
    async def test_called(self, mock_conn_mgr, request_context):
        mock_conn_mgr.return_value.accept_complete = mock.CoroutineMock()
        request_context.message = DIDXComplete()
        handler_inst = test_module.DIDXCompleteHandler()
        await handler_inst.handle(request_context, None)

        mock_conn_mgr.return_value.accept_complete.assert_called_once_with(
            request_context.message, request_context.message_receipt
        )

    @pytest.mark.asyncio
    @mock.patch.object(test_module, "DIDXManager")
    async def test_x(
        self, mock_conn_mgr, request_context, caplog: pytest.LogCaptureFixture
    ):
        mock_conn_mgr.return_value.accept_complete = mock.CoroutineMock(
            side_effect=DIDXManagerError(
                error_code=ProblemReportReason.COMPLETE_NOT_ACCEPTED.value
            )
        )
        mock_conn_mgr.return_value._logger = mock.MagicMock(exception=mock.MagicMock())
        request_context.message = DIDXComplete()
        handler_inst = test_module.DIDXCompleteHandler()
        responder = MockResponder()
        with caplog.at_level("ERROR"):
            await handler_inst.handle(request_context, responder)
        assert "Error receiving connection complete" in caplog.text
