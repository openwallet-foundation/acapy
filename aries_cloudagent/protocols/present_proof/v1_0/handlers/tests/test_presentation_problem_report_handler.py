from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.presentation_problem_report import (
    PresentationProblemReport,
    ProblemReportReason,
)

from .. import presentation_problem_report_handler as test_module


class TestPresentationProblemReportHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            request_context.connection_ready = True
            mock_pres_mgr.return_value.receive_problem_report = (
                async_mock.CoroutineMock()
            )
            request_context.message = PresentationProblemReport(
                description={
                    "en": "Change of plans",
                    "code": ProblemReportReason.ABANDONED.value,
                }
            )
            handler = test_module.PresentationProblemReportHandler()
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
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            request_context.connection_ready = True
            mock_pres_mgr.return_value.receive_problem_report = (
                async_mock.CoroutineMock(
                    side_effect=test_module.StorageError("Disk full")
                )
            )
            request_context.message = PresentationProblemReport(
                description={
                    "en": "Change of plans",
                    "code": ProblemReportReason.ABANDONED.value,
                }
            )
            handler = test_module.PresentationProblemReportHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_pres_mgr.assert_called_once_with(request_context.profile)
        mock_pres_mgr.return_value.receive_problem_report.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        assert not responder.messages
