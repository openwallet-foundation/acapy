"""Test mediate grant message handler."""
import pytest
from asynctest import TestCase as AsyncTestCase

from ......config.injection_context import InjectionContext
from ......connections.models.connection_record import ConnectionRecord
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......storage.base import BaseStorage
from ......storage.basic import BasicStorage
from ......wallet.base import BaseWallet
from ......wallet.basic import BasicWallet
from ...messages.mediate_grant import MediationGrant
from ...models.mediation_record import MediationRecord
from ..mediation_grant_handler import MediationGrantHandler

TEST_CONN_ID = 'conn-id'
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ENDPOINT = 'https://example.com'


class TestMediationGrantHandler(AsyncTestCase):
    """Test mediate grant message handler."""

    async def setUp(self):
        """Setup test dependencies."""
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        self.context.message = MediationGrant(
            endpoint=TEST_ENDPOINT,
            routing_keys=[TEST_VERKEY]
        )
        self.context.connection_ready = True
        self.context.connection_record = ConnectionRecord(connection_id=TEST_CONN_ID)
        self.context.injector.bind_instance(BaseStorage, BasicStorage())
        self.context.injector.bind_instance(BaseWallet, BasicWallet())

    async def test_handler_no_active_connection(self):
        handler, responder = MediationGrantHandler(), MockResponder()
        self.context.connection_ready = False
        with pytest.raises(HandlerException) as exc:
            await handler.handle(self.context, responder)
            assert 'no active connection' in str(exc.value)

    async def test_handler_no_mediation_record(self):
        handler, responder = MediationGrantHandler(), MockResponder()
        with pytest.raises(HandlerException) as exc:
            await handler.handle(self.context, responder)
            assert 'has not been requested' in str(exc.value)

    async def test_handler(self):
        handler, responder = MediationGrantHandler(), MockResponder()
        await MediationRecord(connection_id=TEST_CONN_ID).save(self.context)
        await handler.handle(self.context, responder)
        record = await MediationRecord.retrieve_by_connection_id(
            self.context, TEST_CONN_ID
        )
        assert record
        assert record.state == MediationRecord.STATE_GRANTED
        assert record.endpoint == TEST_ENDPOINT
        assert record.routing_keys == [TEST_VERKEY]
