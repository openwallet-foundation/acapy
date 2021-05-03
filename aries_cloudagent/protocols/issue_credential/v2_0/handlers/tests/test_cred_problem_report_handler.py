from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.cred_problem_report import V20CredProblemReport, ProblemReportReason

from .. import cred_problem_report_handler as test_module


class TestCredProblemReportHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_problem_report = (
                async_mock.CoroutineMock()
            )
            request_context.message = V20CredProblemReport(
                description={
                    "en": "oh no",
                    "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
                }
            )
            handler = test_module.CredProblemReportHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_cred_mgr.assert_called_once_with(request_context.profile)
        mock_cred_mgr.return_value.receive_problem_report.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        assert not responder.messages

    async def test_called_x(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_problem_report = (
                async_mock.CoroutineMock(
                    side_effect=test_module.StorageError("Disk full")
                )
            )
            request_context.message = V20CredProblemReport(
                description={
                    "en": "oh no",
                    "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
                }
            )
            handler = test_module.CredProblemReportHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_cred_mgr.assert_called_once_with(request_context.profile)
        mock_cred_mgr.return_value.receive_problem_report.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        assert not responder.messages
