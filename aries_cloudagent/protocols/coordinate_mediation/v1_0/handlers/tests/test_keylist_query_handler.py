"""Test handler for keylist-query message."""
import pytest
from asynctest import TestCase as AsyncTestCase

from aries_cloudagent.config.injection_context import InjectionContext

from ......config.injection_context import InjectionContext
from ......connections.models.connection_record import ConnectionRecord
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......storage.base import BaseStorage
from ......storage.basic import BasicStorage
from ......wallet.base import BaseWallet
from ......wallet.basic import BasicWallet
from .....problem_report.v1_0.message import ProblemReport
from .....routing.v1_0.models.route_record import RouteRecord
from ...messages.keylist import Keylist
from ...messages.keylist_query import KeylistQuery
from ...models.mediation_record import MediationRecord
from ..keylist_query_handler import KeylistQueryHandler

TEST_CONN_ID = 'conn-id'
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"


class TestKeylistQueryHandler(AsyncTestCase):
    """Test handler for keylist-query message."""

    async def setUp(self):
        """Setup test dependencies."""
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        self.context.message = KeylistQuery()
        self.context.connection_ready = True
        self.context.connection_record = ConnectionRecord(connection_id=TEST_CONN_ID)
        self.context.injector.bind_instance(BaseStorage, BasicStorage())
        self.context.injector.bind_instance(BaseWallet, BasicWallet())

    async def test_handler_no_active_connection(self):
        handler, responder = KeylistQueryHandler(), MockResponder()
        self.context.connection_ready = False
        with pytest.raises(HandlerException) as exc:
            await handler.handle(self.context, responder)
            assert 'no active connection' in str(exc.value)

    async def test_handler_no_record(self):
        handler, responder = KeylistQueryHandler(), MockResponder()
        await handler.handle(self.context, responder)
        assert len(responder.messages) == 1
        result, _target = responder.messages[0]
        assert isinstance(result, ProblemReport)
        assert 'not been granted' in result.explain_ltxt

    async def test_handler_record_not_granted(self):
        handler, responder = KeylistQueryHandler(), MockResponder()
        await MediationRecord(
            state=MediationRecord.STATE_DENIED,
            connection_id=TEST_CONN_ID
        ).save(self.context)
        await handler.handle(self.context, responder)
        assert len(responder.messages) == 1
        result, _target = responder.messages[0]
        assert isinstance(result, ProblemReport)
        assert 'not been granted' in result.explain_ltxt

    async def test_handler(self):
        handler, responder = KeylistQueryHandler(), MockResponder()
        await MediationRecord(
            state=MediationRecord.STATE_GRANTED,
            connection_id=TEST_CONN_ID
        ).save(self.context)
        await RouteRecord(
            connection_id=TEST_CONN_ID,
            recipient_key=TEST_VERKEY
        ).save(self.context)
        await handler.handle(self.context, responder)
        assert len(responder.messages) == 1
        result, _target = responder.messages[0]
        assert isinstance(result, Keylist)
        assert len(result.keys) == 1
        assert result.keys[0].recipient_key == TEST_VERKEY
