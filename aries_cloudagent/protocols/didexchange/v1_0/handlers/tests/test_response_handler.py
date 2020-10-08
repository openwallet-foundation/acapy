import pytest
from asynctest import mock as async_mock

from aries_cloudagent.connections.models import connection_target
from aries_cloudagent.connections.models.diddoc import (
    DIDDoc,
    PublicKey,
    PublicKeyType,
    Service,
)
from aries_cloudagent.messaging.base_handler import HandlerException
from aries_cloudagent.messaging.decorators import AttachDecorator
from aries_cloudagent.messaging.request_context import RequestContext
from aries_cloudagent.messaging.responder import MockResponder

from aries_cloudagent.protocols.trustping.v1_0.messages.ping import Ping

from aries_cloudagent.transport.inbound.receipt import MessageReceipt

from ...handlers import response_handler as handler
from ...manager import Conn23ManagerError
from ...messages.response import Conn23Response
from ...messages.problem_report import ProblemReport, ProblemReportReason


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext()
    ctx.message_receipt = MessageReceipt()
    yield ctx


TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_LABEL = "Label"
TEST_ENDPOINT = "http://localhost"
TEST_IMAGE_URL = "http://aries.ca/images/sample.png"


@pytest.fixture()
def did_doc_attach():
    yield {
        "base64": "...",
        "jws": {
            "header": {
                "kid": "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th"
            },
            "protected": "eyJhbGciOiJFZERTQSIsImlhdCI6MTU4Mzg4..."
            "signature": "3dZWsuru7QAVFUCtTd0s7uc1peYEijx4eyt5..."
        }
    }


class TestResponseHandler:
    @pytest.mark.asyncio
    @async_mock.patch.object(handler, "Conn23Manager")
    async def test_called(self, mock_conn_mgr, request_context):
        mock_conn_mgr.return_value.accept_response = async_mock.CoroutineMock()
        request_context.message = Conn23Response()
        handler_inst = handler.Conn23ResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)

        mock_conn_mgr.assert_called_once_with(request_context)
        mock_conn_mgr.return_value.accept_response.assert_called_once_with(
            request_context.message, request_context.message_receipt
        )
        assert not responder.messages

    @pytest.mark.asyncio
    @async_mock.patch.object(handler, "Conn23Manager")
    async def test_called_auto_ping(self, mock_conn_mgr, request_context):
        request_context.update_settings({"auto_ping_connection": True})
        mock_conn_mgr.return_value.accept_response = async_mock.CoroutineMock()
        request_context.message = Conn23Response()
        handler_inst = handler.Conn23ResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)

        mock_conn_mgr.assert_called_once_with(request_context)
        mock_conn_mgr.return_value.accept_response.assert_called_once_with(
            request_context.message, request_context.message_receipt
        )
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, Ping)

    @pytest.mark.asyncio
    @async_mock.patch.object(handler, "Conn23Manager")
    async def test_problem_report(self, mock_conn_mgr, request_context):
        mock_conn_mgr.return_value.accept_response = async_mock.CoroutineMock()
        mock_conn_mgr.return_value.accept_response.side_effect = Conn23ManagerError(
            error_code=ProblemReportReason.RESPONSE_NOT_ACCEPTED
        )
        request_context.message = Conn23Response()
        handler_inst = handler.Conn23ResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, ProblemReport)
            and result.problem_code == ProblemReportReason.RESPONSE_NOT_ACCEPTED
        )
        assert target == {"target_list": None}

    @pytest.mark.asyncio
    @async_mock.patch.object(handler, "Conn23Manager")
    @async_mock.patch.object(connection_target, "ConnectionTarget")
    async def test_problem_report_did_doc(
        self, mock_conn_target, mock_conn_mgr, request_context, did_doc_attach
    ):
        mock_conn_mgr.return_value.accept_response = async_mock.CoroutineMock()
        mock_conn_mgr.return_value.accept_response.side_effect = Conn23ManagerError(
            error_code=ProblemReportReason.REQUEST_NOT_ACCEPTED
        )
        mock_conn_mgr.return_value.diddoc_connection_targets = async_mock.MagicMock(
            return_value=[mock_conn_target]
        )
        request_context.message = Conn23Response(
            did=TEST_DID,
            did_doc_attach=did_doc_attach
        )
        handler_inst = handler.Conn23ResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, ProblemReport)
            and result.problem_code == ProblemReportReason.REQUEST_NOT_ACCEPTED
        )
        assert target == {"target_list": [mock_conn_target]}

    @pytest.mark.asyncio
    @async_mock.patch.object(handler, "Conn23Manager")
    @async_mock.patch.object(connection_target, "ConnectionTarget")
    async def test_problem_report_did_doc_no_conn_target(
        self, mock_conn_target, mock_conn_mgr, request_context, did_doc_attach
    ):
        mock_conn_mgr.return_value.accept_response = async_mock.CoroutineMock()
        mock_conn_mgr.return_value.accept_response.side_effect = Conn23ManagerError(
            error_code=ProblemReportReason.REQUEST_NOT_ACCEPTED
        )
        mock_conn_mgr.return_value.diddoc_connection_targets = async_mock.MagicMock(
            side_effect=ConnectionManagerError("no target")
        )
        request_context.message = Conn23Response(
            connection=ConnectionDetail(did=TEST_DID, did_doc_attach=did_doc_attach)
        )
        handler_inst = handler.Conn23ResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, ProblemReport)
            and result.problem_code == ProblemReportReason.REQUEST_NOT_ACCEPTED
        )
        assert target == {"target_list": None}
