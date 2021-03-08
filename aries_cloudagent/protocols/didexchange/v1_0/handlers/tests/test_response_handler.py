import pytest
from asynctest import mock as async_mock
from asynctest import TestCase as AsyncTestCase

from ......connections.models import connection_target
from ......connections.models.diddoc_v2 import (
    DIDDoc,
    VerificationMethod,
    PublicKeyType,
    Service,
)
from ......messaging.decorators.attach_decorator import AttachDecorator
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......protocols.trustping.v1_0.messages.ping import Ping
from ......transport.inbound.receipt import MessageReceipt

from ...handlers import response_handler as test_module
from ...manager import DIDXManagerError
from ...messages.response import DIDXResponse
from ...messages.problem_report import ProblemReport, ProblemReportReason

TEST_DID = "did:sov:55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_LABEL = "Label"
TEST_ENDPOINT = "http://localhost"
TEST_IMAGE_URL = "http://aries.ca/images/sample.png"


class TestDIDXResponseHandler(AsyncTestCase):
    def did_doc(self):
        did = TEST_DID
        verkey = TEST_VERKEY
        endpoint = TEST_ENDPOINT
        doc = DIDDoc(did)

        pk = doc.add_verification_method(
            type=PublicKeyType.ED25519_SIG_2018, controller=did, value=verkey, ident="1"
        )

        doc.add_didcomm_service(
            type="IndyAgent", recipient_keys=[pk], routing_keys=[], endpoint=endpoint
        )
        return doc

    async def setUp(self):
        self.ctx = RequestContext.test_context()
        self.ctx.message_receipt = MessageReceipt()

        wallet = (await self.ctx.session()).wallet
        self.did_info = await wallet.create_local_did()

        self.did_doc_attach = AttachDecorator.from_indy_dict(self.did_doc().serialize())
        await self.did_doc_attach.data.sign(self.did_info.verkey, wallet)

        self.request = DIDXResponse(
            did=TEST_DID,
            did_doc_attach=self.did_doc_attach,
        )

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "DIDXManager")
    async def test_called(self, mock_didx_mgr):
        mock_didx_mgr.return_value.accept_response = async_mock.CoroutineMock()
        self.ctx.message = DIDXResponse()
        handler_inst = test_module.DIDXResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)

        mock_didx_mgr.return_value.accept_response.assert_called_once_with(
            self.ctx.message, self.ctx.message_receipt
        )
        assert not responder.messages

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "DIDXManager")
    async def test_called_auto_ping(self, mock_didx_mgr):
        self.ctx.update_settings({"auto_ping_connection": True})
        mock_didx_mgr.return_value.accept_response = async_mock.CoroutineMock()
        self.ctx.message = DIDXResponse()
        handler_inst = test_module.DIDXResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)

        mock_didx_mgr.return_value.accept_response.assert_called_once_with(
            self.ctx.message, self.ctx.message_receipt
        )
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, Ping)

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "DIDXManager")
    async def test_problem_report(self, mock_didx_mgr):
        mock_didx_mgr.return_value.accept_response = async_mock.CoroutineMock(
            side_effect=DIDXManagerError(
                error_code=ProblemReportReason.RESPONSE_NOT_ACCEPTED
            )
        )
        self.ctx.message = DIDXResponse()
        handler_inst = test_module.DIDXResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, ProblemReport)
            and result.problem_code == ProblemReportReason.RESPONSE_NOT_ACCEPTED
        )
        assert target == {"target_list": None}

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "DIDXManager")
    @async_mock.patch.object(connection_target, "ConnectionTarget")
    async def test_problem_report_did_doc(
        self,
        mock_conn_target,
        mock_didx_mgr,
    ):
        mock_didx_mgr.return_value.accept_response = async_mock.CoroutineMock(
            side_effect=DIDXManagerError(
                error_code=ProblemReportReason.RESPONSE_NOT_ACCEPTED
            )
        )
        mock_didx_mgr.return_value.diddoc_connection_targets = async_mock.MagicMock(
            return_value=[mock_conn_target]
        )
        self.ctx.message = DIDXResponse(
            did=TEST_DID,
            did_doc_attach=self.did_doc_attach,
        )
        handler_inst = test_module.DIDXResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, ProblemReport)
            and result.problem_code == ProblemReportReason.RESPONSE_NOT_ACCEPTED
        )
        assert target == {"target_list": [mock_conn_target]}

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "DIDXManager")
    @async_mock.patch.object(connection_target, "ConnectionTarget")
    async def test_problem_report_did_doc_no_conn_target(
        self,
        mock_conn_target,
        mock_didx_mgr,
    ):
        mock_didx_mgr.return_value.accept_response = async_mock.CoroutineMock(
            side_effect=DIDXManagerError(
                error_code=ProblemReportReason.RESPONSE_NOT_ACCEPTED
            )
        )
        mock_didx_mgr.return_value.diddoc_connection_targets = async_mock.MagicMock(
            side_effect=DIDXManagerError("no target")
        )
        self.ctx.message = DIDXResponse(
            did=TEST_DID,
            did_doc_attach=self.did_doc_attach,
        )
        handler_inst = test_module.DIDXResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, ProblemReport)
            and result.problem_code == ProblemReportReason.RESPONSE_NOT_ACCEPTED
        )
        assert target == {"target_list": None}
