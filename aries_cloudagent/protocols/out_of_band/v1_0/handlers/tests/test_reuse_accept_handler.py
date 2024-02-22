"""Test Reuse Accept Message Handler."""

import pytest

from aries_cloudagent.tests import mock

from ......connections.models.conn_record import ConnRecord
from ......core.profile import ProfileSession
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...handlers import reuse_accept_handler as test_module
from ...manager import OutOfBandManagerError
from ...messages.reuse_accept import HandshakeReuseAccept


@pytest.fixture()
async def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    ctx.message_receipt = MessageReceipt()
    yield ctx


@pytest.fixture()
async def connection_record(request_context, session) -> ConnRecord:
    record = ConnRecord()
    request_context.connection_record = record
    await record.save(session)
    yield record


@pytest.fixture()
async def session(request_context) -> ProfileSession:
    yield await request_context.session()


class TestHandshakeReuseAcceptHandler:
    @pytest.mark.asyncio
    @mock.patch.object(test_module, "OutOfBandManager")
    async def test_called(self, mock_oob_mgr, request_context, connection_record):
        mock_oob_mgr.return_value.receive_reuse_accepted_message = mock.CoroutineMock()
        request_context.message = HandshakeReuseAccept()
        handler = test_module.HandshakeReuseAcceptMessageHandler()
        responder = MockResponder()
        await handler.handle(context=request_context, responder=responder)
        mock_oob_mgr.return_value.receive_reuse_accepted_message.assert_called_once_with(
            reuse_accepted_msg=request_context.message,
            receipt=request_context.message_receipt,
            conn_record=connection_record,
        )

    @pytest.mark.asyncio
    @mock.patch.object(test_module, "OutOfBandManager")
    async def test_exception(
        self,
        mock_oob_mgr,
        request_context,
        connection_record,
        caplog: pytest.LogCaptureFixture,
    ):
        mock_oob_mgr.return_value.receive_reuse_accepted_message = mock.CoroutineMock()
        mock_oob_mgr.return_value.receive_reuse_accepted_message.side_effect = (
            OutOfBandManagerError("error")
        )
        request_context.message = HandshakeReuseAccept()
        handler = test_module.HandshakeReuseAcceptMessageHandler()
        responder = MockResponder()
        with caplog.at_level("ERROR"):
            await handler.handle(request_context, responder)
        assert "Error processing" in caplog.text
