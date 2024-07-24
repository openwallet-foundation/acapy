import pytest

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......tests import mock
from ...messages.rotate import Rotate
from .. import rotate_handler as test_module

test_valid_rotate_request = {
    "to_did": "did:example:newdid",
}


@pytest.fixture()
def request_context():
    ctx = RequestContext.test_context()
    yield ctx


class TestRotateHandler:
    """Unit tests for RotateHandler."""

    @pytest.mark.asyncio
    @mock.patch.object(test_module, "DIDRotateManager")
    async def test_handle(self, MockDIDRotateManager, request_context):
        MockDIDRotateManager.return_value.receive_rotate = mock.CoroutineMock()
        MockDIDRotateManager.return_value.commit_rotate = mock.CoroutineMock()

        request_context.message = Rotate(**test_valid_rotate_request)
        request_context.connection_record = mock.MagicMock()
        request_context.connection_ready = True

        handler = test_module.RotateHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)

        MockDIDRotateManager.return_value.receive_rotate.assert_called_once_with(
            request_context.connection_record, request_context.message
        )
        MockDIDRotateManager.return_value.commit_rotate.assert_called_once_with(
            request_context.connection_record,
            MockDIDRotateManager.return_value.receive_rotate.return_value,
        )
