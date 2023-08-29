"""Test Problem Report Handler."""
import pytest

from asynctest import mock as async_mock

from ......connections.models.conn_record import ConnRecord
from ......core.profile import ProfileSession
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...handlers import problem_report_handler as test_module
from ...manager import OutOfBandManagerError
from ...messages.problem_report import OOBProblemReport, ProblemReportReason


@pytest.fixture()
async def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    ctx.message_receipt = MessageReceipt()
    yield ctx


@pytest.fixture()
async def connection_record(request_context, session) -> ConnRecord:
    record = ConnRecord()
    request_context.connection_record = record
    await record.save(session)
    yield record


@pytest.fixture()
async def session(request_context) -> ProfileSession:
    yield await request_context.session()


class TestOOBProblemReportHandler:
    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "OutOfBandManager")
    async def test_called(self, mock_oob_mgr, request_context, connection_record):
        mock_oob_mgr.return_value.receive_problem_report = async_mock.CoroutineMock()
        request_context.message = OOBProblemReport(
            description={
                "en": "No such connection",
                "code": ProblemReportReason.NO_EXISTING_CONNECTION.value,
            }
        )
        handler = test_module.OOBProblemReportMessageHandler()
        handler._logger = async_mock.MagicMock(
            error=async_mock.MagicMock(),
            info=async_mock.MagicMock(),
            warning=async_mock.MagicMock(),
            debug=async_mock.MagicMock(),
        )
        responder = MockResponder()
        await handler.handle(context=request_context, responder=responder)
        mock_oob_mgr.return_value.receive_problem_report.assert_called_once_with(
            problem_report=request_context.message,
            receipt=request_context.message_receipt,
            conn_record=connection_record,
        )

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "OutOfBandManager")
    async def test_exception(self, mock_oob_mgr, request_context, connection_record):
        mock_oob_mgr.return_value.receive_problem_report = async_mock.CoroutineMock()
        mock_oob_mgr.return_value.receive_problem_report.side_effect = (
            OutOfBandManagerError("error")
        )
        request_context.message = OOBProblemReport(
            description={
                "en": "Connection not active",
                "code": ProblemReportReason.EXISTING_CONNECTION_NOT_ACTIVE.value,
            }
        )
        handler = test_module.OOBProblemReportMessageHandler()
        handler._logger = async_mock.MagicMock(
            error=async_mock.MagicMock(),
            info=async_mock.MagicMock(),
            warning=async_mock.MagicMock(),
            debug=async_mock.MagicMock(),
        )
        responder = MockResponder()
        await handler.handle(context=request_context, responder=responder)
        assert handler._logger.exception.call_count == 1
