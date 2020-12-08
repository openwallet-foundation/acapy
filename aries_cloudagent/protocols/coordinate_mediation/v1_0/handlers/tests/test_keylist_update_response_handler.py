"""Test handler for keylist-update-response message."""

import pytest
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

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
from ...messages.inner.keylist_update_rule import KeylistUpdateRule
from ...messages.inner.keylist_updated import KeylistUpdated
from ...messages.keylist_update_response import KeylistUpdateResponse
from ...manager import MediationManager
from ..keylist_update_response_handler import KeylistUpdateResponseHandler

TEST_CONN_ID = 'conn-id'
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"

class TestKeylistUpdateResponseHandler(AsyncTestCase):
    """Test handler for keylist-update-response message."""

    async def setUp(self):
        """Setup test dependencies."""
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        self.updated = [
            KeylistUpdated(
                recipient_key=TEST_VERKEY,
                action=KeylistUpdateRule.RULE_ADD,
                result=KeylistUpdated.RESULT_SUCCESS
            )
        ]
        self.context.message = KeylistUpdateResponse(updated=self.updated)
        self.context.connection_ready = True
        self.context.connection_record = ConnectionRecord(connection_id=TEST_CONN_ID)
        self.context.injector.bind_instance(BaseStorage, BasicStorage())
        self.context.injector.bind_instance(BaseWallet, BasicWallet())

    async def test_handler_no_active_connection(self):
        handler, responder = KeylistUpdateResponseHandler(), MockResponder()
        self.context.connection_ready = False
        with pytest.raises(HandlerException) as exc:
            await handler.handle(self.context, responder)
            assert 'no active connection' in str(exc.value)

    async def test_handler(self):
        handler, responder = KeylistUpdateResponseHandler(), MockResponder()
        with async_mock.patch.object(
            MediationManager, 'store_update_results'
        ) as mock_method:
            await handler.handle(self.context, responder)
            mock_method.assert_called_once_with(TEST_CONN_ID, self.updated)
