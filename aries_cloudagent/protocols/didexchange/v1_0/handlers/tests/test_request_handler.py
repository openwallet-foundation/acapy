from asynctest import mock as async_mock
from asynctest import TestCase as AsyncTestCase

from ......connections.models import conn_record, connection_target
from ......connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from ......core.in_memory import InMemoryProfile
from ......messaging.decorators.attach_decorator import AttachDecorator
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt
from ......wallet.did_method import DIDMethods, SOV
from ......wallet.key_type import ED25519
from ...handlers import request_handler as test_module
from ...manager import DIDXManagerError
from ...messages.problem_report import DIDXProblemReport, ProblemReportReason
from ...messages.request import DIDXRequest

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_LABEL = "Label"
TEST_ENDPOINT = "http://localhost"
TEST_IMAGE_URL = "http://aries.ca/images/sample.png"


class TestDIDXRequestHandler(AsyncTestCase):
    """Class unit testing request handler."""

    def did_doc(self):
        doc = DIDDoc(did=TEST_DID)
        controller = TEST_DID
        ident = "1"
        pk_value = TEST_VERKEY
        pk = PublicKey(
            TEST_DID,
            ident,
            pk_value,
            PublicKeyType.ED25519_SIG_2018,
            controller,
            False,
        )
        doc.set(pk)
        recip_keys = [pk]
        router_keys = []
        service = Service(
            TEST_DID,
            "indy",
            "IndyAgent",
            recip_keys,
            router_keys,
            TEST_ENDPOINT,
        )
        doc.set(service)
        return doc

    async def setUp(self):
        self.ctx = RequestContext.test_context()
        self.ctx.message_receipt = MessageReceipt(
            recipient_did="dummy",
            recipient_did_public=True,
        )
        self.session = InMemoryProfile.test_session(
            {
                "default_endpoint": "http://localhost",
                "default_label": "This guy",
                "additional_endpoints": ["http://aries.ca/another-endpoint"],
                "debug.auto_accept_invites": True,
                "debug.auto_accept_requests_peer": True,
                "debug.auto_accept_requests_public": True,
            }
        )
        self.session.profile.context.injector.bind_instance(DIDMethods, DIDMethods())

        self.conn_rec = conn_record.ConnRecord(
            my_did="55GkHamhTU1ZbTbV2ab9DE",
            their_did="GbuDUYXaUZRfHD2jeDuQuP",
            their_public_did="55GkHamhTU1ZbTbV2ab9DE",
            invitation_msg_id="12345678-1234-5678-1234-567812345678",
            their_role=conn_record.ConnRecord.Role.REQUESTER,
        )
        await self.conn_rec.save(self.session)

        wallet = self.session.wallet
        self.did_info = await wallet.create_local_did(method=SOV, key_type=ED25519)

        self.did_doc_attach = AttachDecorator.data_base64(self.did_doc().serialize())
        await self.did_doc_attach.data.sign(self.did_info.verkey, wallet)

        self.request = DIDXRequest(
            label=TEST_LABEL,
            did=TEST_DID,
            did_doc_attach=self.did_doc_attach,
        )

    @async_mock.patch.object(test_module, "DIDXManager")
    async def test_called(self, mock_didx_mgr):
        mock_didx_mgr.return_value.receive_request = async_mock.CoroutineMock()
        self.ctx.message = DIDXRequest()
        handler_inst = test_module.DIDXRequestHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)

        mock_didx_mgr.return_value.receive_request.assert_called_once_with(
            request=self.ctx.message,
            recipient_did=self.ctx.message_receipt.recipient_did,
            recipient_verkey=None,
        )
        assert not responder.messages

    @async_mock.patch.object(test_module, "DIDXManager")
    async def test_called_with_auto_response(self, mock_didx_mgr):
        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.accept = conn_record.ConnRecord.ACCEPT_AUTO
        mock_conn_rec.save = async_mock.CoroutineMock()
        mock_didx_mgr.return_value.receive_request = async_mock.CoroutineMock(
            return_value=mock_conn_rec
        )
        mock_didx_mgr.return_value.create_response = async_mock.CoroutineMock()
        self.ctx.message = DIDXRequest()
        handler_inst = test_module.DIDXRequestHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)

        mock_didx_mgr.return_value.receive_request.assert_called_once_with(
            request=self.ctx.message,
            recipient_did=self.ctx.message_receipt.recipient_did,
            recipient_verkey=None,
        )
        mock_didx_mgr.return_value.create_response.assert_called_once_with(
            mock_conn_rec, mediation_id=None
        )
        assert responder.messages

    @async_mock.patch.object(test_module, "DIDXManager")
    async def test_connection_record_with_mediation_metadata_auto_response(
        self, mock_didx_mgr
    ):
        test_exist_conn = conn_record.ConnRecord(
            my_did="did:sov:LjgpST2rjsoxYegQDRm7EL",
            their_did="did:sov:LjgpST2rjsoxYegQDRm7EL",
            their_public_did="did:sov:LjgpST2rjsoxYegQDRm7EL",
            invitation_msg_id="12345678-1234-5678-1234-567812345678",
            their_role=conn_record.ConnRecord.Role.REQUESTER,
        )
        test_exist_conn.metadata_get = async_mock.CoroutineMock(
            return_value={"id": "mediation-test-id"}
        )
        test_exist_conn.accept = conn_record.ConnRecord.ACCEPT_AUTO
        test_exist_conn.save = async_mock.CoroutineMock()
        mock_didx_mgr.return_value.receive_request = async_mock.CoroutineMock(
            return_value=test_exist_conn
        )
        mock_didx_mgr.return_value.create_response = async_mock.CoroutineMock()
        test_ctx = RequestContext.test_context()
        test_ctx.message = DIDXRequest()
        test_ctx.message_receipt = MessageReceipt()
        test_ctx.connection_record = test_exist_conn
        responder = MockResponder()
        handler_inst = test_module.DIDXRequestHandler()
        await handler_inst.handle(test_ctx, responder)
        mock_didx_mgr.return_value.create_response.assert_called_once_with(
            test_exist_conn, mediation_id="mediation-test-id"
        )
        assert responder.messages

    @async_mock.patch.object(test_module, "DIDXManager")
    async def test_problem_report(self, mock_didx_mgr):
        mock_didx_mgr.return_value.receive_request = async_mock.CoroutineMock(
            side_effect=DIDXManagerError(
                error_code=ProblemReportReason.REQUEST_NOT_ACCEPTED.value
            )
        )
        self.ctx.message = DIDXRequest()
        handler_inst = test_module.DIDXRequestHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, DIDXProblemReport)
            and result.description
            and (
                result.description["code"]
                == ProblemReportReason.REQUEST_NOT_ACCEPTED.value
            )
        )
        assert target == {"target_list": None}

    @async_mock.patch.object(test_module, "DIDXManager")
    @async_mock.patch.object(connection_target, "ConnectionTarget")
    async def test_problem_report_did_doc(self, mock_conn_target, mock_didx_mgr):
        mock_didx_mgr.return_value.receive_request = async_mock.CoroutineMock(
            side_effect=DIDXManagerError(
                error_code=ProblemReportReason.REQUEST_NOT_ACCEPTED.value
            )
        )
        mock_didx_mgr.return_value.diddoc_connection_targets = async_mock.MagicMock(
            return_value=[mock_conn_target]
        )
        self.ctx.message = DIDXRequest(
            label=TEST_LABEL,
            did=TEST_DID,
            did_doc_attach=self.did_doc_attach,
        )
        handler_inst = test_module.DIDXRequestHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, DIDXProblemReport)
            and result.description
            and (
                result.description["code"]
                == ProblemReportReason.REQUEST_NOT_ACCEPTED.value
            )
        )
        assert target == {"target_list": [mock_conn_target]}

    @async_mock.patch.object(test_module, "DIDXManager")
    @async_mock.patch.object(connection_target, "ConnectionTarget")
    async def test_problem_report_did_doc_no_conn_target(
        self,
        mock_conn_target,
        mock_didx_mgr,
    ):
        mock_didx_mgr.return_value.receive_request = async_mock.CoroutineMock(
            side_effect=DIDXManagerError(
                error_code=ProblemReportReason.REQUEST_NOT_ACCEPTED.value
            )
        )
        mock_didx_mgr.return_value.diddoc_connection_targets = async_mock.MagicMock(
            side_effect=DIDXManagerError("no targets")
        )
        self.ctx.message = DIDXRequest(
            label=TEST_LABEL,
            did=TEST_DID,
            did_doc_attach=self.did_doc_attach,
        )
        handler_inst = test_module.DIDXRequestHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, DIDXProblemReport)
            and result.description
            and (
                result.description["code"]
                == ProblemReportReason.REQUEST_NOT_ACCEPTED.value
            )
        )
        assert target == {"target_list": None}
