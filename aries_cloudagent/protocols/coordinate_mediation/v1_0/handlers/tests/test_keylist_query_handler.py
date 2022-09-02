"""Test handler for keylist-query message."""
import pytest
from asynctest import TestCase as AsyncTestCase

from ......config.injection_context import InjectionContext
from ......connections.models.conn_record import ConnRecord
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from .....routing.v1_0.models.route_record import RouteRecord

from ...messages.keylist import Keylist
from ...messages.keylist_query import KeylistQuery
from ...messages.problem_report import CMProblemReport, ProblemReportReason
from ...models.mediation_record import MediationRecord

from ..keylist_query_handler import KeylistQueryHandler

TEST_CONN_ID = "conn-id"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_VERKEY_DIDKEY = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"


class TestKeylistQueryHandler(AsyncTestCase):
    """Test handler for keylist-query message."""

    async def setUp(self):
        """Setup test dependencies."""
        self.context = RequestContext.test_context()
        self.session = await self.context.session()
        self.session = await self.context.session()
        self.context.message = KeylistQuery()
        self.context.connection_ready = True
        self.context.connection_record = ConnRecord(connection_id=TEST_CONN_ID)

    async def test_handler_no_active_connection(self):
        handler, responder = KeylistQueryHandler(), MockResponder()
        self.context.connection_ready = False
        with pytest.raises(HandlerException) as exc:
            await handler.handle(self.context, responder)
            assert "no active connection" in str(exc.value)

    async def test_handler_no_record(self):
        handler, responder = KeylistQueryHandler(), MockResponder()
        await handler.handle(self.context, responder)
        assert len(responder.messages) == 1
        result, _target = responder.messages[0]
        assert isinstance(result, CMProblemReport)
        assert (
            result.description["code"]
            == ProblemReportReason.MEDIATION_NOT_GRANTED.value
        )

    async def test_handler_record_not_granted(self):
        handler, responder = KeylistQueryHandler(), MockResponder()
        await MediationRecord(
            state=MediationRecord.STATE_DENIED, connection_id=TEST_CONN_ID
        ).save(self.session)
        await handler.handle(self.context, responder)
        assert len(responder.messages) == 1
        result, _target = responder.messages[0]
        assert isinstance(result, CMProblemReport)
        assert (
            result.description["code"]
            == ProblemReportReason.MEDIATION_NOT_GRANTED.value
        )

    async def test_handler(self):
        handler, responder = KeylistQueryHandler(), MockResponder()
        await MediationRecord(
            state=MediationRecord.STATE_GRANTED, connection_id=TEST_CONN_ID
        ).save(self.session)
        await RouteRecord(connection_id=TEST_CONN_ID, recipient_key=TEST_VERKEY).save(
            self.session
        )
        await handler.handle(self.context, responder)
        assert len(responder.messages) == 1
        result, _target = responder.messages[0]
        assert isinstance(result, Keylist)
        assert len(result.keys) == 1
        assert result.keys[0].recipient_key == TEST_VERKEY_DIDKEY
