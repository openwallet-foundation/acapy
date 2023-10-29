from asynctest import mock as async_mock
import pytest

from .. import problem_report_handler as test_module
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ...manager import DIDXManagerError
from ...messages.problem_report import DIDXProblemReport


@pytest.fixture()
def request_context():
    ctx = RequestContext.test_context()
    yield ctx


class TestDIDXProblemReportHandler:
    """Unit test problem report handler."""

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "DIDXManager")
    async def test_called(self, manager, request_context):
        manager.return_value.receive_problem_report = async_mock.CoroutineMock()
        request_context.message = DIDXProblemReport()
        request_context.connection_record = async_mock.MagicMock()
        handler_inst = test_module.DIDXProblemReportHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)
        assert not responder.messages
        assert manager.return_value.receive_problem_report.called_once()

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "DIDXManager")
    async def test_called_no_conn(self, manager, request_context):
        manager.return_value.receive_problem_report = async_mock.CoroutineMock()
        request_context.message = DIDXProblemReport()
        handler_inst = test_module.DIDXProblemReportHandler()
        responder = MockResponder()
        with pytest.raises(HandlerException):
            await handler_inst.handle(request_context, responder)

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "DIDXManager")
    async def test_called_unrecognized_report_exception(
        self, manager, request_context, caplog
    ):
        manager.return_value.receive_problem_report = async_mock.CoroutineMock(
            side_effect=DIDXManagerError()
        )
        request_context.message = DIDXProblemReport()
        request_context.connection_record = async_mock.MagicMock()
        handler_inst = test_module.DIDXProblemReportHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)
        assert "Error receiving DID Exchange problem report" in caplog.text
