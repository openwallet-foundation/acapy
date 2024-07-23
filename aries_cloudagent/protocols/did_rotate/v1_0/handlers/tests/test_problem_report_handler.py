import pytest

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......tests import mock
from ...messages.problem_report import RotateProblemReport
from .. import problem_report_handler as test_module

test_valid_rotate_request = {
    "to_did": "did:example:newdid",
}


@pytest.fixture()
def request_context():
    ctx = RequestContext.test_context()
    yield ctx


class TestProblemReportHandler:
    """Unit tests for ProblemReportHandler."""

    @pytest.mark.asyncio
    @mock.patch.object(test_module, "DIDRotateManager")
    async def test_handle(self, MockDIDRotateManager, request_context):
        MockDIDRotateManager.return_value.receive_problem_report = mock.CoroutineMock()

        request_context.message = RotateProblemReport()
        request_context.connection_record = mock.MagicMock()
        request_context.connection_ready = True

        handler = test_module.ProblemReportHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)

        MockDIDRotateManager.return_value.receive_problem_report.assert_called_once_with(
            request_context.message
        )
