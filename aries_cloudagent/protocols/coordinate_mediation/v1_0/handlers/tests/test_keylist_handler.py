"""Test keylist handler."""
import logging

import pytest

from ......config.injection_context import InjectionContext
from ......connections.models.conn_record import ConnRecord
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......storage.base import BaseStorage
from ......storage.in_memory import InMemoryStorage
from ......wallet.base import BaseWallet
from ......wallet.in_memory import InMemoryWallet
from ...messages.keylist import Keylist
from ...models.mediation_record import MediationRecord
from ..keylist_handler import KeylistHandler

TEST_CONN_ID = "conn-id"
pytestmark = pytest.mark.asyncio


@pytest.fixture
def context():
    """Fixture for context used in tests."""
    # pylint: disable=W0621
    context = RequestContext(
        base_context=InjectionContext(enforce_typing=False)
    )
    context.message = Keylist()
    context.connection_record = ConnectionRecord(connection_id=TEST_CONN_ID)
    context.connection_ready = True
    context.injector.bind_instance(BaseStorage, BasicStorage())
    context.injector.bind_instance(BaseWallet, BasicWallet())
    yield context


class TestKeylistHandler:
    """Test keylist handler."""
    # pylint: disable=W0621

    async def test_handler_no_active_connection(self, context):
        handler, responder = KeylistHandler(), MockResponder()
        context.connection_ready = False
        with pytest.raises(HandlerException) as exc:
            await handler.handle(context, responder)
            assert 'inactive connection' in exc.value

    async def test_handler_no_record(self, context, caplog):
        caplog.set_level(logging.INFO)
        handler, responder = KeylistHandler(), MockResponder()
        await handler.handle(context, responder)
        assert 'not acting as mediator' in caplog.text
        assert 'Keylist received: ' not in caplog.text

    async def test_handler(self, context, caplog):
        caplog.set_level(logging.INFO)
        handler, responder = KeylistHandler(), MockResponder()
        await MediationRecord(
            connection_id=TEST_CONN_ID
        ).save(context)
        await handler.handle(context, responder)
        assert 'Keylist received: ' in caplog.text
