from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aries_cloudagent.config.injection_context import InjectionContext
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder

from .. import mediate_request_handler as TestModule
_handler = TestModule.MediationRequestHandler()
from ...messages.mediate_request import MediationRequest as request
from ...messages.mediate_grant import MediationGrant as response
from ...messages.mediate_deny import MediationDeny as denied

"""
    Tests for Mediation based on "0211: Mediator Coordination Protocol" aries-rfc. 
"""


class TestMediationRequestHandler:
    async def setUp(self): # needed?
        """setup dependencies of messaging"""

        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        self.context.message = request()

    async def test_handler(self):
        """ test mediation handler """
        handler, responder = _handler(), MockResponder()

        mediate_request = request( mediator_terms = [], recipient_terms = [] )
        with async_mock.patch.object(
            TestModule, "ConnectionManager", autospec=True
        ) as mock_mgr:
            await handler.handle(self.context,responder)


    async def test_for_denied_mediation_request(self):
        """ Test for MEDIATE_REQUEST request that results in MEDIATE_DENY response. """
        handler, responder = _handler(), MockResponder()

        #TODO: update terms to real terms
        mediate_request = request( mediator_terms = [False], recipient_terms = [False] ) 
        with async_mock.patch.object(
            TestModule, "ConnectionManager", autospec=True
        ) as mock_mgr:
            await handler.handle(self.context,responder)
            messages = responder.messages

            assert messages
            assert len(messages) == 1
            
            (result, _) = messages[0]
            assert type(result) == denied
            assert result._thread._thid == self.context.message._message_id

    
    async def test_for_granted_mediation_request(self):
        """ Test for MEDIATE_REQUEST request that results in MEDIATE_GRANT response. """
        handler, responder = _handler(), MockResponder()

        #TODO: update terms to real terms
        mediate_request = request( mediator_terms = [True], recipient_terms = [True] ) 
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