from aries_cloudagent.tests import mock
from unittest import IsolatedAsyncioTestCase

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.pres_problem_report import V20PresProblemReport, ProblemReportReason

from .. import pres_problem_report_handler as test_module


class TestV20PresProblemReportHandler(IsolatedAsyncioTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = mock.MagicMock()

        with mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_problem_report = mock.CoroutineMock()
            request_context.message = V20PresProblemReport(
                description={
                    "en": "Change of plans",
                    "code": ProblemReportReason.ABANDONED.value,
                }
            )
            handler = test_module.V20PresProblemReportHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_pres_mgr.assert_called_once_with(request_context.profile)
        mock_pres_mgr.return_value.receive_problem_report.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        assert not responder.messages

    async def test_called_x(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = mock.MagicMock()

        with mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_problem_report = mock.CoroutineMock(
                side_effect=test_module.StorageError("Disk full")
            )
            request_context.message = V20PresProblemReport(
                description={
                    "en": "Change of plans",
                    "code": ProblemReportReason.ABANDONED.value,
                }
            )
            handler = test_module.V20PresProblemReportHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_pres_mgr.assert_called_once_with(request_context.profile)
        mock_pres_mgr.return_value.receive_problem_report.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        assert not responder.messages
