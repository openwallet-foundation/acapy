from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aries_cloudagent.config.injection_context import InjectionContext
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder

from .. import keylist_update_handler as TestModule
_handler = TestModule.KeylistUpdateHandler()
from ...messages.keylist_update_response import KeylistUpdateResponse as response
from ...messages.keylist_update import KeylistUpdate as update
from ...messages.keylist_query import KeylistQuery as query


"""
    Tests for Mediation based on "0211: Mediator Coordination Protocol" aries-rfc. 
"""


class TestKeyListUpdateRequestHandler:

    async def test_update_handle(self):
        handler, responder = _handler(), MockResponder()

        mediate_request = update( updates = [])
        with async_mock.patch.object(
            TestModule, "ConnectionManager", autospec=True
        ) as mock_mgr:
            await handler.handle(self.context,responder)
    
    async def test_query_handle(self):
        handler, responder = _handler(), MockResponder()

        mediate_request = query( filter = None, paginate = None)
        with async_mock.patch.object(
            TestModule, "ConnectionManager", autospec=True
        ) as mock_mgr:
            await handler.handle(self.context,responder)

    async def test_updated_response(self):
        handler, responder = _handler(), MockResponder()

        mediate_request = update( updates = [])
        with async_mock.patch.object(
            TestModule, "ConnectionManager", autospec=True
        ) as mock_mgr:
            await handler.handle(self.context,responder)
            messages = responder.messages

            assert messages
            assert len(messages) == 1
            
            (result, _) = messages[0]
            assert type(result) == response
            assert result._thread._thid == self.context.message._message_id

