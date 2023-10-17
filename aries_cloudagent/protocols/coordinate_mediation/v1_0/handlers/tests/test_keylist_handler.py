"""Test keylist handler."""
import pytest

from asynctest import mock as async_mock

from ......connections.models.conn_record import ConnRecord
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ...messages.keylist import Keylist
from ...models.mediation_record import MediationRecord
from ..keylist_handler import KeylistHandler

from .. import keylist_handler as test_module

TEST_CONN_ID = "conn-id"
pytestmark = pytest.mark.asyncio


@pytest.fixture
def context():
    """Fixture for context used in tests."""
    # pylint: disable=W0621
    context = RequestContext.test_context()
    context.message = Keylist()
    context.connection_record = ConnRecord(connection_id=TEST_CONN_ID)
    context.connection_ready = True
    yield context


@pytest.fixture
async def session(context):  # pylint: disable=W0621
    """Fixture for session used in tests"""
    yield await context.session()


class TestKeylistHandler:
    """Test keylist handler."""

    # pylint: disable=W0621

    async def test_handler_no_active_connection(self, context):
        handler, responder = KeylistHandler(), MockResponder()
        context.connection_ready = False
        with pytest.raises(HandlerException) as exc:
            await handler.handle(context, responder)
            assert "inactive connection" in exc.value

    async def test_handler_no_record(self, context):
        with async_mock.patch.object(
            test_module, "LOG", async_mock.MagicMock()
        ) as mock_logger:
            handler, responder = KeylistHandler(), MockResponder()
            await handler.handle(context, responder)
            assert mock_logger.warning.call_count == 1
            assert mock_logger.info.call_count == 0

    async def test_handler(self, context, session):
        with async_mock.patch.object(
            test_module, "LOG", async_mock.MagicMock()
        ) as mock_logger:
            handler, responder = KeylistHandler(), MockResponder()
            await MediationRecord(connection_id=TEST_CONN_ID).save(session)
            await handler.handle(context, responder)
            assert mock_logger.info.call_count == 1
