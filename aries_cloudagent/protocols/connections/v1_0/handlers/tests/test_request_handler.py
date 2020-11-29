import pytest
from asynctest import mock as async_mock

from ......connections.models import connection_target
from ......connections.models.diddoc import (
    DIDDoc,
    PublicKey,
    PublicKeyType,
    Service,
)
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...handlers import connection_request_handler as handler
from ...manager import ConnectionManagerError
from ...messages.connection_request import ConnectionRequest
from ...messages.problem_report import ProblemReport, ProblemReportReason
from ...models.connection_detail import ConnectionDetail


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    ctx.message_receipt = MessageReceipt()
    yield ctx


TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_LABEL = "Label"
TEST_ENDPOINT = "http://localhost"
TEST_IMAGE_URL = "http://aries.ca/images/sample.png"


@pytest.fixture()
def did_doc():
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
    yield doc


class TestRequestHandler:
    @pytest.mark.asyncio
    @async_mock.patch.object(handler, "ConnectionManager")
    async def test_called(self, mock_conn_mgr, request_context):
        mock_conn_mgr.return_value.receive_request = async_mock.CoroutineMock()
        request_context.message = ConnectionRequest()
        handler_inst = handler.ConnectionRequestHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)

        mock_conn_mgr.assert_called_once_with(request_context)
        mock_conn_mgr.return_value.receive_request.assert_called_once_with(
            request_context.message, request_context.message_receipt
        )
        assert not responder.messages

    @pytest.mark.asyncio
    @async_mock.patch.object(handler, "ConnectionManager")
    async def test_problem_report(self, mock_conn_mgr, request_context):
        mock_conn_mgr.return_value.receive_request = async_mock.CoroutineMock()
        mock_conn_mgr.return_value.receive_request.side_effect = ConnectionManagerError(
            error_code=ProblemReportReason.REQUEST_NOT_ACCEPTED
        )
        request_context.message = ConnectionRequest()
        handler_inst = handler.ConnectionRequestHandler()
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

    @pytest.mark.asyncio
    @async_mock.patch.object(handler, "ConnectionManager")
    @async_mock.patch.object(connection_target, "ConnectionTarget")
    async def test_problem_report_did_doc(
        self, mock_conn_target, mock_conn_mgr, request_context, did_doc
    ):
        mock_conn_mgr.return_value.receive_request = async_mock.CoroutineMock()
        mock_conn_mgr.return_value.receive_request.side_effect = ConnectionManagerError(
            error_code=ProblemReportReason.REQUEST_NOT_ACCEPTED
        )
        mock_conn_mgr.return_value.diddoc_connection_targets = async_mock.MagicMock(
            return_value=[mock_conn_target]
        )
        request_context.message = ConnectionRequest(
            connection=ConnectionDetail(did=TEST_DID, did_doc=did_doc),
            label=TEST_LABEL,
            image_url=TEST_IMAGE_URL,
        )
        handler_inst = handler.ConnectionRequestHandler()
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
    @async_mock.patch.object(handler, "ConnectionManager")
    @async_mock.patch.object(connection_target, "ConnectionTarget")
    async def test_problem_report_did_doc_no_conn_target(
        self, mock_conn_target, mock_conn_mgr, request_context, did_doc
    ):
        mock_conn_mgr.return_value.receive_request = async_mock.CoroutineMock()
        mock_conn_mgr.return_value.receive_request.side_effect = ConnectionManagerError(
            error_code=ProblemReportReason.REQUEST_NOT_ACCEPTED
        )
        mock_conn_mgr.return_value.diddoc_connection_targets = async_mock.MagicMock(
            side_effect=ConnectionManagerError("no targets")
        )
        request_context.message = ConnectionRequest(
            connection=ConnectionDetail(did=TEST_DID, did_doc=did_doc),
            label=TEST_LABEL,
            image_url=TEST_IMAGE_URL,
        )
        handler_inst = handler.ConnectionRequestHandler()
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
