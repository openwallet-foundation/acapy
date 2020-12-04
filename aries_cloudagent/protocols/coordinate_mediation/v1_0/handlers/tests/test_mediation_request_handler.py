"""Test mediate request message handler."""
import pytest
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aries_cloudagent.config.injection_context import InjectionContext

from ......connections.models.connection_record import ConnectionRecord
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......protocols.problem_report.v1_0.message import ProblemReport
from ......storage.base import BaseStorage
from ......storage.basic import BasicStorage
from ......wallet.base import BaseWallet
from ......wallet.basic import BasicWallet
from ...messages.mediate_request import MediationRequest
from ...messages.mediate_grant import MediationGrant
from ...models.mediation_record import MediationRecord
from ..mediate_request_handler import MediationRequestHandler

TEST_CONN_ID = 'conn-id'
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"

class TestMediationRequestHandler(AsyncTestCase):
    """Test mediate request message handler."""

    async def setUp(self):
        """setup dependencies of messaging"""
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        self.context.message = MediationRequest()
        self.context.connection_ready = True
        self.context.connection_record = ConnectionRecord(connection_id=TEST_CONN_ID)
        self.context.injector.bind_instance(BaseStorage, BasicStorage())
        self.context.injector.bind_instance(BaseWallet, BasicWallet())

    async def test_handler_no_active_connection(self):
        """ test mediation handler """
        handler, responder = MediationRequestHandler(), MockResponder()
        self.context.connection_ready = False
        with pytest.raises(HandlerException) as exc:
            await handler.handle(self.context,responder)
            assert 'no active connection' in str(exc.value)

    async def test_handler_mediation_record_already_exists(self):
        handler, responder = MediationRequestHandler(), MockResponder()
        await MediationRecord(connection_id=TEST_CONN_ID).save(self.context)
        await handler.handle(self.context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, _target = messages[0]
        assert isinstance(result, ProblemReport)

    async def test_handler(self):
        handler, responder = MediationRequestHandler(), MockResponder()
        await handler.handle(self.context, responder)
        record = await MediationRecord.retrieve_by_connection_id(self.context, TEST_CONN_ID)
        assert record
        assert record.state == MediationRecord.STATE_REQUEST_RECEIVED

    async def test_handler_open_mediation(self):
        handler, responder = MediationRequestHandler(), MockResponder()
        self.context.settings.set_value('mediation.open', True)
        await handler.handle(self.context, responder)
        record = await MediationRecord.retrieve_by_connection_id(self.context, TEST_CONN_ID)
        assert record
        assert record.state == MediationRecord.STATE_GRANTED
        messages = responder.messages
        assert len(messages) == 1
        result, _target = messages[0]
        assert isinstance(result, MediationGrant)
