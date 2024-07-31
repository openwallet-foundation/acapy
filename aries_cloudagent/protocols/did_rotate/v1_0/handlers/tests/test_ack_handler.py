import pytest

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......tests import mock
from ...messages.ack import RotateAck
from .. import ack_handler as test_module


@pytest.fixture()
def request_context():
    ctx = RequestContext.test_context()
    yield ctx


class TestAckHandler:
    """Unit tests for AckHandler."""

    @pytest.mark.asyncio
    @mock.patch.object(test_module, "DIDRotateManager")
    async def test_handle(self, MockDIDRotateManager, request_context):
        MockDIDRotateManager.return_value.receive_ack = mock.CoroutineMock()

        request_context.message = RotateAck()
        request_context.connection_record = mock.MagicMock()
        request_context.connection_ready = True

        handler = test_module.RotateAckHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)

        MockDIDRotateManager.return_value.receive_ack.assert_called_once_with(
            request_context.connection_record, request_context.message
        )
