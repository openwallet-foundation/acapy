"""Test Reuse Message Handler."""
import pytest

from asynctest import mock as async_mock

from ......connections.models import connection_target
from ......connections.models.conn_record import ConnRecord
from ......connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from ......core.profile import ProfileSession
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......storage.base import BaseStorage
from ......storage.error import StorageNotFoundError
from ......transport.inbound.receipt import MessageReceipt

from ...handlers import reuse_handler as test_module
from ...manager import OutOfBandManagerError, OutOfBandManager
from ...messages.reuse import HandshakeReuse
from ...messages.reuse_accept import HandshakeReuseAccept


@pytest.fixture()
async def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    ctx.message_receipt = MessageReceipt()
    yield ctx


@pytest.fixture()
async def session(request_context) -> ProfileSession:
    yield await request_context.session()


class TestHandshakeReuseHandler:
    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "OutOfBandManager")
    async def test_called(self, mock_oob_mgr, request_context):
        mock_oob_mgr.return_value.receive_reuse_message = async_mock.CoroutineMock()
        request_context.message = HandshakeReuse()
        handler = test_module.HandshakeReuseMessageHandler()
        request_context.connection_record = ConnRecord()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        mock_oob_mgr.return_value.receive_reuse_message.assert_called_once_with(
            request_context.message,
            request_context.message_receipt,
            request_context.connection_record,
        )

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "OutOfBandManager")
    async def test_reuse_accepted(self, mock_oob_mgr, request_context):
        mock_oob_mgr.return_value.receive_reuse_message = async_mock.CoroutineMock()
        reuse_accepted = HandshakeReuseAccept()
        mock_oob_mgr.return_value.receive_reuse_message.return_value = reuse_accepted
        request_context.message = HandshakeReuse()
        handler = test_module.HandshakeReuseMessageHandler()
        request_context.connection_record = ConnRecord()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        mock_oob_mgr.return_value.receive_reuse_message.assert_called_once_with(
            request_context.message,
            request_context.message_receipt,
            request_context.connection_record,
        )

    @pytest.mark.asyncio
    @async_mock.patch.object(test_module, "OutOfBandManager")
    async def test_exception(self, mock_oob_mgr, request_context):
        mock_oob_mgr.return_value.receive_reuse_message = async_mock.CoroutineMock()
        mock_oob_mgr.return_value.receive_reuse_message.side_effect = (
            OutOfBandManagerError("error")
        )
        request_context.message = HandshakeReuse()
        handler = test_module.HandshakeReuseMessageHandler()
        request_context.connection_record = ConnRecord()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        assert mock_oob_mgr.return_value._logger.exception.called_once_("error")
