"""Test Reuse Message Handler."""

from typing import AsyncGenerator

import pytest
import pytest_asyncio

from ......connections.models.conn_record import ConnRecord
from ......core.profile import ProfileSession
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......tests import mock
from ......transport.inbound.receipt import MessageReceipt
from ......utils.testing import create_test_profile
from ...handlers import reuse_handler as test_module
from ...manager import OutOfBandManagerError
from ...messages.reuse import HandshakeReuse
from ...messages.reuse_accept import HandshakeReuseAccept


@pytest_asyncio.fixture
async def request_context():
    ctx = RequestContext.test_context(await create_test_profile())
    ctx.message_receipt = MessageReceipt()
    yield ctx


@pytest_asyncio.fixture
async def session(request_context) -> AsyncGenerator[ProfileSession, None]:
    yield await request_context.session()


class TestHandshakeReuseHandler:
    @pytest.mark.asyncio
    @mock.patch.object(test_module, "OutOfBandManager")
    async def test_called(self, mock_oob_mgr, request_context):
        mock_oob_mgr.return_value.receive_reuse_message = mock.CoroutineMock()
        request_context.message = HandshakeReuse()
        handler = test_module.HandshakeReuseMessageHandler()
        request_context.connection_record = ConnRecord()
        request_context.connection_ready = True
        responder = MockResponder()
        await handler.handle(request_context, responder)
        mock_oob_mgr.return_value.receive_reuse_message.assert_called_once_with(
            request_context.message,
            request_context.message_receipt,
            request_context.connection_record,
        )

    @pytest.mark.asyncio
    @mock.patch.object(test_module, "OutOfBandManager")
    async def test_reuse_accepted(self, mock_oob_mgr, request_context):
        mock_oob_mgr.return_value.receive_reuse_message = mock.CoroutineMock()
        reuse_accepted = HandshakeReuseAccept()
        mock_oob_mgr.return_value.receive_reuse_message.return_value = reuse_accepted
        request_context.message = HandshakeReuse()
        handler = test_module.HandshakeReuseMessageHandler()
        request_context.connection_record = ConnRecord()
        request_context.connection_ready = True
        responder = MockResponder()
        await handler.handle(request_context, responder)
        mock_oob_mgr.return_value.receive_reuse_message.assert_called_once_with(
            request_context.message,
            request_context.message_receipt,
            request_context.connection_record,
        )

    @pytest.mark.asyncio
    @mock.patch.object(test_module, "OutOfBandManager")
    async def test_exception(
        self, mock_oob_mgr, request_context, caplog: pytest.LogCaptureFixture
    ):
        mock_oob_mgr.return_value.receive_reuse_message = mock.CoroutineMock()
        mock_oob_mgr.return_value.receive_reuse_message.side_effect = (
            OutOfBandManagerError("error")
        )
        request_context.message = HandshakeReuse()
        handler = test_module.HandshakeReuseMessageHandler()
        request_context.connection_record = ConnRecord()
        request_context.connection_ready = True
        responder = MockResponder()
        with caplog.at_level("ERROR"):
            await handler.handle(request_context, responder)
        assert "Error processing" in caplog.text
