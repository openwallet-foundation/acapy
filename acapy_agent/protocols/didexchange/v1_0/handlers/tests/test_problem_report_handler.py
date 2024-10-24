import pytest

from acapy_agent.tests import mock

from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......utils.testing import create_test_profile
from ...manager import DIDXManagerError
from ...messages.problem_report import DIDXProblemReport
from .. import problem_report_handler as test_module


@pytest.fixture()
async def request_context():
    yield RequestContext.test_context(await create_test_profile())


class TestDIDXProblemReportHandler:
    """Unit test problem report handler."""

    @pytest.mark.asyncio
    @mock.patch.object(test_module, "DIDXManager")
    async def test_called(self, manager, request_context):
        manager.return_value.receive_problem_report = mock.CoroutineMock()
        request_context.message = DIDXProblemReport()
        request_context.connection_record = mock.MagicMock()
        handler_inst = test_module.DIDXProblemReportHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)
        assert not responder.messages
        manager.return_value.receive_problem_report.assert_called_once()

    @pytest.mark.asyncio
    @mock.patch.object(test_module, "DIDXManager")
    async def test_called_no_conn(self, manager, request_context):
        manager.return_value.receive_problem_report = mock.CoroutineMock()
        request_context.message = DIDXProblemReport()
        handler_inst = test_module.DIDXProblemReportHandler()
        responder = MockResponder()
        with pytest.raises(HandlerException):
            await handler_inst.handle(request_context, responder)

    @pytest.mark.asyncio
    @mock.patch.object(test_module, "DIDXManager")
    async def test_called_unrecognized_report_exception(
        self, manager, request_context, caplog
    ):
        manager.return_value.receive_problem_report = mock.CoroutineMock(
            side_effect=DIDXManagerError()
        )
        request_context.message = DIDXProblemReport()
        request_context.connection_record = mock.MagicMock()
        handler_inst = test_module.DIDXProblemReportHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)
        assert "Error receiving DID Exchange problem report" in caplog.text
