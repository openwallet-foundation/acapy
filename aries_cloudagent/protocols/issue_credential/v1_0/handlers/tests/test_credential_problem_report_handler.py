from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.credential_problem_report import (
    CredentialProblemReport,
    ProblemReportReason,
)

from .. import credential_problem_report_handler as test_module


class TestCredentialProblemReportHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_cred_mgr:
            request_context.connection_ready = True
            mock_cred_mgr.return_value.receive_problem_report = (
                async_mock.CoroutineMock()
            )
            request_context.message = CredentialProblemReport(
                description={
                    "en": "Change of plans",
                    "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
                }
            )
            handler = test_module.CredentialProblemReportHandler()
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
            test_module, "CredentialManager", autospec=True
        ) as mock_cred_mgr:
            request_context.connection_ready = True
            mock_cred_mgr.return_value.receive_problem_report = (
                async_mock.CoroutineMock(
                    side_effect=test_module.StorageError("Disk full")
                )
            )
            request_context.message = CredentialProblemReport(
                description={
                    "en": "Change of plans",
                    "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
                }
            )
            handler = test_module.CredentialProblemReportHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_cred_mgr.assert_called_once_with(request_context.profile)
        mock_cred_mgr.return_value.receive_problem_report.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        assert not responder.messages

    async def test_called_not_ready(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_ready = False

        request_context.message = CredentialProblemReport(
            description={
                "en": "Change of plans",
                "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
            }
        )
        handler = test_module.CredentialProblemReportHandler()
        responder = MockResponder()

        with self.assertRaises(test_module.HandlerException) as err:
            await handler.handle(request_context, responder)
        assert (
            err.exception.message
            == "Connection used for credential problem report not ready"
        )

    async def test_called_no_connection(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = None

        request_context.message = CredentialProblemReport(
            description={
                "en": "Change of plans",
                "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
            }
        )
        handler = test_module.CredentialProblemReportHandler()
        responder = MockResponder()

        with self.assertRaises(test_module.HandlerException) as err:
            await handler.handle(request_context, responder)
        assert (
            err.exception.message
            == "Connectionless not supported for credential problem report"
        )

        assert not responder.messages
