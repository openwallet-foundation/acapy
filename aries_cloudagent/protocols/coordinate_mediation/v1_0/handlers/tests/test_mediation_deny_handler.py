"""Test mediate deny message handler."""

import pytest
from unittest import IsolatedAsyncioTestCase

from ......connections.models.conn_record import ConnRecord
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ...messages.mediate_deny import MediationDeny
from ...models.mediation_record import MediationRecord
from ..mediation_deny_handler import MediationDenyHandler

TEST_CONN_ID = "conn-id"


class TestMediationDenyHandler(IsolatedAsyncioTestCase):
    """Test mediate deny message handler."""

    async def asyncSetUp(self):
        """Setup test dependencies."""
        self.context = RequestContext.test_context()
        self.session = await self.context.session()
        self.context.message = MediationDeny()
        self.context.connection_ready = True
        self.context.connection_record = ConnRecord(connection_id=TEST_CONN_ID)

    async def test_handler_no_active_connection(self):
        handler, responder = MediationDenyHandler(), MockResponder()
        self.context.connection_ready = False
        with pytest.raises(HandlerException) as exc:
            await handler.handle(self.context, responder)
            assert "no active connection" in str(exc.value)

    async def test_handler_no_mediation_record(self):
        handler, responder = MediationDenyHandler(), MockResponder()
        with pytest.raises(HandlerException) as exc:
            await handler.handle(self.context, responder)
            assert "has not been requested" in str(exc.value)

    async def test_handler(self):
        handler, responder = MediationDenyHandler(), MockResponder()
        await MediationRecord(connection_id=TEST_CONN_ID).save(self.session)
        await handler.handle(self.context, responder)
        record = await MediationRecord.retrieve_by_connection_id(
            self.session, TEST_CONN_ID
        )
        assert record
        assert record.state == MediationRecord.STATE_DENIED
