from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.cred_issue import V20CredIssue

from .. import cred_issue_handler as test_module


class TestCredentialIssueHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.settings["debug.auto_store_credential"] = False
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_credential = async_mock.CoroutineMock()
            request_context.message = V20CredIssue()
            request_context.connection_ready = True
            handler_inst = test_module.V20CredIssueHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_cred_mgr.assert_called_once_with(request_context.profile)
        mock_cred_mgr.return_value.receive_credential.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        assert not responder.messages

    async def test_called_auto_store(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.settings["debug.auto_store_credential"] = True
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value = async_mock.MagicMock(
                receive_credential=async_mock.CoroutineMock(),
                store_credential=async_mock.CoroutineMock(),
                send_cred_ack=async_mock.CoroutineMock(return_value="cred_ack_message"),
            )
            request_context.message = V20CredIssue()
            request_context.connection_ready = True
            handler_inst = test_module.V20CredIssueHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_cred_mgr.assert_called_once_with(request_context.profile)
        mock_cred_mgr.return_value.receive_credential.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        assert mock_cred_mgr.return_value.send_cred_ack.call_count == 1

    async def test_called_auto_store_x(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.settings["debug.auto_store_credential"] = True
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value = async_mock.MagicMock(
                receive_credential=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        save_error_state=async_mock.CoroutineMock()
                    )
                ),
                store_credential=async_mock.CoroutineMock(
                    side_effect=[
                        test_module.IndyHolderError,
                        test_module.StorageError(),
                    ]
                ),
                send_cred_ack=async_mock.CoroutineMock(),
            )

            request_context.message = V20CredIssue()
            request_context.connection_ready = True
            handler_inst = test_module.V20CredIssueHandler()
            responder = MockResponder()

            await handler_inst.handle(request_context, responder)  # holder error
            await handler_inst.handle(request_context, responder)  # storage error
            assert mock_cred_mgr.return_value.send_cred_ack.call_count == 2

    async def test_called_not_ready(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_credential = async_mock.CoroutineMock()
            request_context.message = V20CredIssue()
            request_context.connection_ready = False
            handler_inst = test_module.V20CredIssueHandler()
            responder = MockResponder()
            with self.assertRaises(test_module.HandlerException):
                await handler_inst.handle(request_context, responder)

        assert not responder.messages
