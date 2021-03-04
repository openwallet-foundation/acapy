from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from ......messaging.decorators.attach_decorator import AttachDecorator
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.cred_request import V20CredRequest
from ...messages.cred_format import V20CredFormat
from ...messages.cred_proposal import V20CredProposal
from ...messages.inner.cred_preview import V20CredAttrSpec, V20CredPreview
from ...models.cred_ex_record import V20CredExRecord

from .. import cred_request_handler as test_module

CD_ID = "LjgpST2rjsoxYegQDRm7EL:3:CL:18:tag"


class TestV20CredRequestHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
            mock_cred_mgr.return_value.receive_request.return_value.auto_issue = False
            request_context.message = V20CredRequest()
            request_context.connection_ready = True
            handler_inst = test_module.V20CredRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_cred_mgr.assert_called_once_with(request_context.profile)
        mock_cred_mgr.return_value.receive_request.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        assert not responder.messages

    async def test_called_auto_issue(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        attr_values = {"test": "123", "hello": "world"}
        cred_preview = V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=k, value=v) for (k, v) in attr_values.items()
            ]
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            filters_attach=[
                AttachDecorator.data_base64(
                    {
                        "cred_def_id": "LjgpST2rjsoxYegQDRm7EL:3:CL:12:tag1",
                    },
                    ident="0",
                )
            ],
        )
        cred_ex_rec = V20CredExRecord(cred_proposal=cred_proposal.serialize())

        with async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=cred_ex_rec
            )
            mock_cred_mgr.return_value.receive_request.return_value.auto_issue = True
            mock_cred_mgr.return_value.issue_credential = async_mock.CoroutineMock(
                return_value=(None, "cred_issue_message")
            )
            request_context.message = V20CredRequest()
            request_context.connection_ready = True
            handler_inst = test_module.V20CredRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)
            mock_cred_mgr.return_value.issue_credential.assert_called_once_with(
                cred_ex_record=cred_ex_rec, comment=None
            )

        mock_cred_mgr.assert_called_once_with(request_context.profile)
        mock_cred_mgr.return_value.receive_request.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "cred_issue_message"
        assert target == {}

    async def test_called_auto_issue_no_preview(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        cred_proposal = V20CredProposal(
            credential_preview=None,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            filters_attach=[
                AttachDecorator.data_base64(
                    {"cred_def_id": "LjgpST2rjsoxYegQDRm7EL:3:CL:12:tag1"},
                    ident="0",
                )
            ],
        )
        cred_ex_rec = V20CredExRecord(cred_proposal=cred_proposal.serialize())

        with async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=cred_ex_rec
            )
            mock_cred_mgr.return_value.receive_request.return_value.auto_issue = True
            mock_cred_mgr.return_value.issue_credential = async_mock.CoroutineMock(
                return_value=(None, "cred_issue_message")
            )

            request_context.message = V20CredRequest()
            request_context.connection_ready = True
            handler_inst = test_module.V20CredRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)
            mock_cred_mgr.return_value.issue_credential.assert_not_called()

        mock_cred_mgr.assert_called_once_with(request_context.profile)
        mock_cred_mgr.return_value.receive_request.assert_called_once_with(
            request_context.message, request_context.connection_record.connection_id
        )
        assert not responder.messages

    async def test_called_not_ready(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.receive_request = async_mock.CoroutineMock()
            request_context.message = V20CredRequest()
            request_context.connection_ready = False
            handler_inst = test_module.V20CredRequestHandler()
            responder = MockResponder()
            with self.assertRaises(test_module.HandlerException):
                await handler_inst.handle(request_context, responder)

        assert not responder.messages
