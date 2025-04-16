"""Test keylist handler."""

import logging

import pytest
import pytest_asyncio

from ......connections.models.conn_record import ConnRecord
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......utils.testing import create_test_profile
from ...messages.keylist import Keylist
from ...models.mediation_record import MediationRecord
from ..keylist_handler import KeylistHandler

TEST_CONN_ID = "conn-id"
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def context():
    """Fixture for context used in tests."""
    # pylint: disable=W0621
    context = RequestContext.test_context(await create_test_profile())
    context.message = Keylist()
    context.connection_record = ConnRecord(connection_id=TEST_CONN_ID)
    context.connection_ready = True
    yield context


@pytest_asyncio.fixture
async def session(context):  # pylint: disable=W0621
    """Fixture for session used in tests"""
    yield await context.session()


class TestKeylistHandler:
    """Test keylist handler."""

    # pylint: disable=W0621

    async def test_handler_no_active_connection(self, context):
        handler, responder = KeylistHandler(), MockResponder()
        context.connection_ready = False
        with pytest.raises(HandlerException):
            await handler.handle(context, responder)

    async def test_handler_no_record(self, context, caplog):
        handler, responder = KeylistHandler(), MockResponder()
        logging.propagate = True
        caplog.set_level(logging.INFO)
        await handler.handle(context, responder)
        assert "not acting as mediator" in caplog.text
        assert "Keylist received: " not in caplog.text

    async def test_handler(self, context, session, caplog):
        handler, responder = KeylistHandler(), MockResponder()
        await MediationRecord(connection_id=TEST_CONN_ID).save(session)
        logging.propagate = True
        caplog.set_level(logging.INFO)
        await handler.handle(context, responder)
        assert "Keylist received: " in caplog.text
