import pytest

from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder

#from ...handlers.mediate_request_handler import MediationRequestHandler
#from ...messages.mediate_request import MediationRequest
#from ...messages.mediate_grant import MediationGrant

"""
"""


class TestMediationRequestHandler:
    @pytest.mark.asyncio
    async def test_mediation_request(self):
        ctx = RequestContext()
        
        assert True
