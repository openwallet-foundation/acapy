import pytest

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......tests import mock
from ...messages.hangup import Hangup
from .. import hangup_handler as test_module


@pytest.fixture()
def request_context():
    ctx = RequestContext.test_context()
    yield ctx


class TestHangupHandler:
    """Unit tests for HangupHandler."""

    @pytest.mark.asyncio
    @mock.patch.object(test_module, "DIDRotateManager")
    async def test_handle(self, MockDIDRotateManager, request_context):
        MockDIDRotateManager.return_value.receive_hangup = mock.CoroutineMock()

        request_context.message = Hangup()
        request_context.connection_record = mock.MagicMock()
        request_context.connection_ready = True

        handler = test_module.HangupHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)

        MockDIDRotateManager.return_value.receive_hangup.assert_called_once_with(
            request_context.connection_record
        )
